// frontend/src/components/SQLEditor.tsx
import Editor, { type Monaco } from '@monaco-editor/react';
import { useCallback, useRef, useEffect } from 'react';
import type { editor } from 'monaco-editor';

interface SQLEditorProps {
    value: string;
    onChange: (value: string) => void;
    onExecute?: () => void;
    height?: string;
    tables?: Array<{ table_name: string; columns: Array<{ column_name: string }> }>;
}

export function SQLEditor({ value, onChange, onExecute, height = '200px', tables = [] }: SQLEditorProps) {
    const editorRef = useRef<editor.IStandaloneCodeEditor | null>(null);
    const monacoRef = useRef<Monaco | null>(null);
    const onExecuteRef = useRef(onExecute);
    const tablesRef = useRef(tables);

    // ref 업데이트
    useEffect(() => {
        onExecuteRef.current = onExecute;
    }, [onExecute]);

    useEffect(() => {
        tablesRef.current = tables;
    }, [tables]);

    const handleMount = useCallback((editor: editor.IStandaloneCodeEditor, monaco: Monaco) => {
        editorRef.current = editor;
        monacoRef.current = monaco;

        // Ctrl/Cmd + Enter로 실행
        editor.addAction({
            id: 'execute-sql',
            label: 'Execute SQL',
            keybindings: [
                monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter
            ],
            run: () => {
                if (onExecuteRef.current) onExecuteRef.current();
            }
        });

        // SQL 자동완성 등록 (한 번만 등록하고 tablesRef 사용)
        monaco.languages.registerCompletionItemProvider('sql', {
            provideCompletionItems: (model: any, position: any) => {
                const word = model.getWordUntilPosition(position);
                const range = {
                    startLineNumber: position.lineNumber,
                    endLineNumber: position.lineNumber,
                    startColumn: word.startColumn,
                    endColumn: word.endColumn
                };

                // 커서 이전 텍스트(한 줄) 기반으로 컨텍스트 판단 (파서 없이도 안정적)
                const linePrefix: string = model.getLineContent(position.lineNumber).slice(0, position.column - 1);
                const prefixUpper = linePrefix.toUpperCase();

                // 마지막 토큰/키워드 주변 컨텍스트
                const endsWithFromJoin =
                    /\b(FROM|JOIN|INTO|UPDATE)\s+$/i.test(linePrefix) ||
                    /\b(FROM|JOIN|INTO|UPDATE)\s+[A-Z0-9_]*$/i.test(prefixUpper);

                const endsWithSelectWhereOn =
                    /\b(SELECT|WHERE|AND|OR|ON|HAVING|GROUP BY|ORDER BY)\s+$/i.test(prefixUpper) ||
                    /\b(SELECT|WHERE|AND|OR|ON|HAVING)\s+[A-Z0-9_]*$/i.test(prefixUpper);

                const hasDot = /\b[A-Z0-9_]+\.$/i.test(linePrefix);

                // 중복 제거용
                const seen = new Set<string>();
                const suggestions: any[] = [];

                const push = (item: any) => {
                    const key = `${item.kind}:${item.label}`;
                    if (seen.has(key)) return;
                    seen.add(key);
                    suggestions.push(item);
                };

                // 키워드 목록(기존 유지)
                const keywords = [
                    'SELECT', 'FROM', 'WHERE', 'AND', 'OR', 'NOT', 'IN', 'LIKE', 'BETWEEN',
                    'JOIN', 'LEFT JOIN', 'RIGHT JOIN', 'INNER JOIN', 'OUTER JOIN',
                    'ON', 'GROUP BY', 'HAVING', 'ORDER BY', 'ASC', 'DESC',
                    'LIMIT', 'OFFSET', 'AS', 'DISTINCT', 'COUNT', 'SUM', 'AVG', 'MAX', 'MIN',
                    'CASE', 'WHEN', 'THEN', 'ELSE', 'END', 'NULL', 'IS NULL', 'IS NOT NULL',
                    'UNION', 'UNION ALL', 'EXCEPT', 'INTERSECT',
                    'COALESCE', 'NULLIF', 'CAST', 'EXTRACT', 'DATE_TRUNC',
                    'ROW_NUMBER', 'RANK', 'DENSE_RANK', 'NTILE', 'LAG', 'LEAD',
                    'OVER', 'PARTITION BY', 'WITH', 'RECURSIVE'
                ];

                // 1) FROM/JOIN 뒤에서는 "테이블" 위주
                if (endsWithFromJoin) {
                    tablesRef.current.forEach(t => {
                        push({
                            label: t.table_name,
                            kind: monaco.languages.CompletionItemKind.Struct, // Class 대신 Struct로 정규화(의미/안정성)
                            insertText: t.table_name,
                            detail: 'Table',
                            range,
                            sortText: `1_${t.table_name}`
                        });
                    });

                    // 그래도 최소 키워드 조금은 보여주고 싶으면 제한적으로
                    ['SELECT', 'WHERE', 'JOIN', 'LEFT JOIN', 'GROUP BY', 'ORDER BY', 'LIMIT'].forEach(kw => {
                        push({
                            label: kw,
                            kind: monaco.languages.CompletionItemKind.Keyword,
                            insertText: kw,
                            range,
                            sortText: `9_${kw}`
                        });
                    });

                    return { suggestions };
                }

                // 2) 점(.) 직후에는 "컬럼" 우선 (table.column 패턴)
                if (hasDot) {
                    // 마지막 토큰(tableName.) 추출
                    const m = linePrefix.match(/([A-Z0-9_]+)\.$/i);
                    const tableToken = m?.[1];

                    const table = tablesRef.current.find(t => t.table_name.toLowerCase() === (tableToken || '').toLowerCase());

                    if (table) {
                        table.columns.forEach(c => {
                            push({
                                label: c.column_name,
                                kind: monaco.languages.CompletionItemKind.Field,
                                insertText: c.column_name,
                                detail: `Column in ${table.table_name}`,
                                range,
                                sortText: `1_${c.column_name}`
                            });
                        });
                        return { suggestions };
                    }

                    // 테이블을 못 찾으면 전체 컬럼을 낮은 우선순위로
                    tablesRef.current.forEach(t => {
                        t.columns.forEach(c => {
                            push({
                                label: c.column_name,
                                kind: monaco.languages.CompletionItemKind.Field,
                                insertText: c.column_name,
                                detail: 'Column',
                                range,
                                sortText: `5_${c.column_name}`
                            });
                        });
                    });
                    return { suggestions };
                }

                // 3) SELECT/WHERE/ON 등에서는 "컬럼 + 함수 + 키워드" 위주
                if (endsWithSelectWhereOn) {
                    // 컬럼(중복 제거 + 우선순위 높게)
                    tablesRef.current.forEach(t => {
                        t.columns.forEach(c => {
                            push({
                                label: c.column_name,
                                kind: monaco.languages.CompletionItemKind.Field,
                                insertText: c.column_name,
                                detail: 'Column',
                                range,
                                sortText: `1_${c.column_name}`
                            });
                        });
                    });

                    // 함수(Keyword로 넣으면 혼란이 있어 Function으로 정규화)
                    ['COUNT', 'SUM', 'AVG', 'MIN', 'MAX', 'COALESCE', 'NULLIF', 'CAST', 'EXTRACT', 'DATE_TRUNC'].forEach(fn => {
                        push({
                            label: fn,
                            kind: monaco.languages.CompletionItemKind.Function,
                            insertText: fn,
                            detail: 'Function',
                            range,
                            sortText: `2_${fn}`
                        });
                    });

                    // 키워드(우선순위 낮게)
                    keywords.forEach(kw => {
                        push({
                            label: kw,
                            kind: monaco.languages.CompletionItemKind.Keyword,
                            insertText: kw,
                            range,
                            sortText: `9_${kw}`
                        });
                    });

                    return { suggestions };
                }

                // 4) 그 외 일반 상태: 키워드 + 테이블 + 컬럼(우선순위 조정)
                keywords.forEach(kw => {
                    push({
                        label: kw,
                        kind: monaco.languages.CompletionItemKind.Keyword,
                        insertText: kw,
                        range,
                        sortText: `3_${kw}`
                    });
                });

                tablesRef.current.forEach(t => {
                    push({
                        label: t.table_name,
                        kind: monaco.languages.CompletionItemKind.Struct,
                        insertText: t.table_name,
                        detail: 'Table',
                        range,
                        sortText: `1_${t.table_name}`
                    });

                    t.columns.forEach(c => {
                        push({
                            label: c.column_name,
                            kind: monaco.languages.CompletionItemKind.Field,
                            insertText: c.column_name,
                            detail: 'Column',
                            range,
                            sortText: `2_${c.column_name}`
                        });
                    });
                });

                return { suggestions };
            }

        });
    }, []); // tables 의존성 제거

    return (
        <div className="sql-editor">
            <Editor
                height={height}
                defaultLanguage="sql"
                theme="vs-dark"
                value={value}
                onChange={(val) => onChange(val || '')}
                onMount={handleMount}
                options={{
                    minimap: { enabled: false },
                    fontSize: 14,
                    lineHeight: 20,
                    suggestLineHeight: 28,
                    renderLineHighlight: 'all',
                    lineNumbers: 'on',
                    scrollBeyondLastLine: false,
                    automaticLayout: true,
                    tabSize: 2,
                    wordWrap: 'on',
                    padding: { top: 10, bottom: 10 },
                    suggestOnTriggerCharacters: true,
                    quickSuggestions: true,
                    fixedOverflowWidgets: true,
                    suggest: {
                        showKeywords: true,
                        showSnippets: false,
                        showClasses: false,
                        showConstants: false,
                        showFields: true,
                        showFunctions: true,
                        showInterfaces: false,
                        preview: true,
                    },
                }}
            />
        </div>
    );
}
