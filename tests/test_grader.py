# tests/test_grader.py
"""
Grader 모듈 단위 테스트
"""
import pytest
import pandas as pd
from grader.checker import compare_frames, LogicError


class TestCompareFrames:
    """compare_frames 함수 테스트"""
    
    def test_identical_frames(self):
        """동일한 DataFrame은 오류 없이 통과"""
        df1 = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})
        df2 = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})
        # 오류 없이 완료되어야 함
        compare_frames(df1, df2)
    
    def test_column_mismatch(self):
        """컬럼 불일치 시 LogicError 발생"""
        df1 = pd.DataFrame({"a": [1], "b": [2]})
        df2 = pd.DataFrame({"a": [1], "c": [2]})
        
        with pytest.raises(LogicError, match="SCHEMA_MISMATCH"):
            compare_frames(df1, df2)
    
    def test_row_count_mismatch(self):
        """행 수 불일치 시 LogicError 발생"""
        df1 = pd.DataFrame({"a": [1, 2, 3]})
        df2 = pd.DataFrame({"a": [1, 2]})
        
        with pytest.raises(LogicError, match="ROW_COUNT_MISMATCH"):
            compare_frames(df1, df2)
    
    def test_value_mismatch(self):
        """값 불일치 시 LogicError 발생"""
        df1 = pd.DataFrame({"a": [1, 2]})
        df2 = pd.DataFrame({"a": [1, 3]})
        
        with pytest.raises(LogicError, match="VALUE_MISMATCH"):
            compare_frames(df1, df2)
    
    def test_with_sort_keys(self):
        """정렬 키 적용 후 비교"""
        df1 = pd.DataFrame({"id": [2, 1], "val": ["b", "a"]})
        df2 = pd.DataFrame({"id": [1, 2], "val": ["a", "b"]})
        # 정렬 후 동일하므로 통과
        compare_frames(df1, df2, sort_keys=["id"])
    
    def test_float_tolerance(self):
        """실수 비교 시 오차 허용"""
        df1 = pd.DataFrame({"a": [1.0000000001]})
        df2 = pd.DataFrame({"a": [1.0000000002]})
        # 기본 tolerance(1e-9) 내이므로 통과
        compare_frames(df1, df2)
    
    def test_null_handling(self):
        """NaN 값 비교 (둘 다 NaN이면 일치)"""
        df1 = pd.DataFrame({"a": [1, None]})
        df2 = pd.DataFrame({"a": [1, None]})
        compare_frames(df1, df2)
