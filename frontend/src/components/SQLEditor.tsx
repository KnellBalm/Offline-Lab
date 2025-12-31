// frontend/src/components/SQLEditor.tsx
import Editor, { type Monaco } from '@monaco-editor/react';
import { useCallback, useRef, useEffect } from 'react';
import type { editor } from 'monaco-editor';
import { useTheme } from '../contexts/ThemeContext';

interface SQLEditorProps {
    value: string;
    onChange: (value: string) => void;
    onExecute?: () => void;
    height?: string;
    tables?: Array<{ table_name: string; columns: Array<{ column_name: string }> }>;
}

export function SQLEditor({ value, onChange, onExecute, height = '200px', tables = [] }: SQLEditorProps) {
    const { theme } = useTheme();
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
                    // label만으로 중복 제거 (kind 무관)
                    if (seen.has(item.label)) return;
                    seen.add(item.label);
                    suggestions.push(item);
                };

                // PostgreSQL 키워드 + 함수 목록 (쿼리 분석용만 유지)
                const keywords = [
                    // SELECT 분석용 키워드
                    'SELECT', 'FROM', 'WHERE', 'AND', 'OR', 'NOT', 'IN', 'LIKE', 'ILIKE', 'BETWEEN',
                    'JOIN', 'LEFT JOIN', 'RIGHT JOIN', 'INNER JOIN', 'FULL OUTER JOIN', 'CROSS JOIN',
                    'ON', 'USING', 'GROUP BY', 'HAVING', 'ORDER BY', 'ASC', 'DESC', 'NULLS FIRST', 'NULLS LAST',
                    'LIMIT', 'OFFSET', 'AS', 'DISTINCT', 'DISTINCT ON', 'ALL',
                    'CASE', 'WHEN', 'THEN', 'ELSE', 'END', 'NULL', 'IS NULL', 'IS NOT NULL',
                    'UNION', 'UNION ALL', 'EXCEPT', 'INTERSECT',
                    'WITH', 'RECURSIVE', 'LATERAL',
                    // DDL/DML 키워드 (쿼리 테스트에서는 사용 안함)
                    // 'INSERT INTO', 'VALUES', 'UPDATE', 'SET', 'DELETE FROM', 'RETURNING',
                    // 'CREATE TABLE', 'ALTER TABLE', 'DROP TABLE', 'TRUNCATE',
                    // 'CREATE INDEX', 'CREATE VIEW', 'CREATE FUNCTION',
                    // PostgreSQL 집계 함수
                    'COUNT', 'SUM', 'AVG', 'MAX', 'MIN', 'ARRAY_AGG', 'STRING_AGG',
                    // PostgreSQL 윈도우 함수
                    'ROW_NUMBER', 'RANK', 'DENSE_RANK', 'NTILE', 'LAG', 'LEAD',
                    'FIRST_VALUE', 'LAST_VALUE', 'NTH_VALUE', 'OVER', 'PARTITION BY',
                    // PostgreSQL 문자열 함수
                    'CONCAT', 'LENGTH', 'LOWER', 'UPPER', 'TRIM', 'SUBSTRING', 'REPLACE', 'SPLIT_PART',
                    // PostgreSQL 날짜/시간 함수
                    'NOW', 'CURRENT_DATE', 'CURRENT_TIMESTAMP',
                    'DATE_TRUNC', 'DATE_PART', 'EXTRACT', 'AGE', 'INTERVAL',
                    'TO_DATE', 'TO_TIMESTAMP', 'TO_CHAR',
                    // PostgreSQL 조건 함수
                    'COALESCE', 'NULLIF', 'GREATEST', 'LEAST', 'CAST',
                    // PostgreSQL 수학 함수
                    'ABS', 'CEIL', 'FLOOR', 'ROUND', 'TRUNC', 'MOD',
                    // PostgreSQL 연산자
                    'EXISTS', 'NOT EXISTS', 'ANY'
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
                    // 전체 쿼리에서 사용된 테이블 추출
                    const fullText = model.getValue().toUpperCase();
                    const tableMatches = fullText.match(/\b(FROM|JOIN)\s+([A-Z_][A-Z0-9_]*)/gi) || [];
                    const usedTables = new Set<string>();
                    tableMatches.forEach((match: string) => {
                        const parts = match.split(/\s+/);
                        if (parts.length >= 2) {
                            usedTables.add(parts[parts.length - 1].toLowerCase());
                        }
                    });

                    // 사용된 테이블의 컬럼만 표시 (테이블 없으면 전체 표시)
                    const tablesToShow = usedTables.size > 0
                        ? tablesRef.current.filter(t => usedTables.has(t.table_name.toLowerCase()))
                        : tablesRef.current;

                    // 중복 컬럼 찾기
                    const columnCount = new Map<string, string[]>();
                    tablesToShow.forEach(t => {
                        t.columns.forEach(c => {
                            const colName = c.column_name.toLowerCase();
                            if (!columnCount.has(colName)) {
                                columnCount.set(colName, []);
                            }
                            columnCount.get(colName)!.push(t.table_name);
                        });
                    });

                    // 컬럼 추가 (중복 컬럼은 table.column 형태로)
                    tablesToShow.forEach(t => {
                        t.columns.forEach(c => {
                            const colName = c.column_name.toLowerCase();
                            const tables = columnCount.get(colName) || [];

                            if (tables.length > 1) {
                                // 중복 컬럼: table.column 형태로 추가
                                push({
                                    label: `${t.table_name}.${c.column_name}`,
                                    kind: monaco.languages.CompletionItemKind.Field,
                                    insertText: `${t.table_name}.${c.column_name}`,
                                    detail: `Column (${tables.length} tables)`,
                                    range,
                                    sortText: `1_${c.column_name}`
                                });
                            } else {
                                // 유일 컬럼: 그냥 컬럼 이름만
                                push({
                                    label: c.column_name,
                                    kind: monaco.languages.CompletionItemKind.Field,
                                    insertText: c.column_name,
                                    detail: `${t.table_name}`,
                                    range,
                                    sortText: `1_${c.column_name}`
                                });
                            }
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
                theme={theme === 'dark' ? 'vs-dark' : 'light'}
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
                    quickSuggestions: {
                        other: "on",      // 일반 코드에서 suggest 활성화
                        comments: "off",
                        strings: "off"
                    },
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
