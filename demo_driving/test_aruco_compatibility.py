import cv2 as cv
import numpy as np

def test_opencv_aruco_compatibility():
    """OpenCV 4.6.0에서 ArUco 호환성 확인"""
    print("=== OpenCV ArUco 호환성 테스트 ===")
    print(f"OpenCV 버전: {cv.__version__}")
    
    # 1. ArUco 모듈 속성 확인
    print("\n1. ArUco 모듈 속성 확인:")
    try:
        print(f"   cv.aruco 존재: {hasattr(cv, 'aruco')}")
        if hasattr(cv, 'aruco'):
            aruco_attrs = [attr for attr in dir(cv.aruco) if not attr.startswith('_')]
            print(f"   ArUco 함수/클래스 개수: {len(aruco_attrs)}")
            
            important_functions = [
                'getPredefinedDictionary',
                'DetectorParameters', 
                'detectMarkers',
                'drawDetectedMarkers',
                'estimatePoseSingleMarkers'
            ]
            
            for func in important_functions:
                exists = hasattr(cv.aruco, func)
                print(f"   {func}: {'✅' if exists else '❌'}")
    except Exception as e:
        print(f"   ArUco 모듈 확인 실패: {e}")
    
    # 2. 다른 방식으로 ArUco 접근 시도
    print("\n2. 대체 ArUco 접근 방법:")
    
    # 방법 1: cv2.aruco 직접 import
    try:
        import cv2.aruco as aruco_module
        print("   ✅ cv2.aruco 직접 import 성공")
        
        # 딕셔너리 생성 테스트
        dict_aruco = aruco_module.getPredefinedDictionary(aruco_module.DICT_5X5_250)
        param_aruco = aruco_module.DetectorParameters()
        print("   ✅ 직접 import로 ArUco 객체 생성 성공")
        
        return ('direct_import', aruco_module, dict_aruco, param_aruco)
        
    except Exception as e:
        print(f"   ❌ cv2.aruco 직접 import 실패: {e}")
    
    # 방법 2: 레거시 API 시도 (OpenCV 3.x 스타일)
    try:
        print("   레거시 ArUco API 확인 중...")
        
        # OpenCV 3.x 스타일 함수들 확인
        legacy_functions = [
            'aruco_Dictionary_get',
            'aruco_DetectorParameters_create',
            'aruco_detectMarkers'
        ]
        
        for func in legacy_functions:
            if hasattr(cv, func):
                print(f"     {func}: ✅")
            else:
                print(f"     {func}: ❌")
        
    except Exception as e:
        print(f"   레거시 API 확인 실패: {e}")
    
    # 방법 3: 기본 방식으로 재시도
    try:
        print("   기본 ArUco API 재시도...")
        aruco_dict = cv.aruco.getPredefinedDictionary(cv.aruco.DICT_5X5_250)
        parameters = cv.aruco.DetectorParameters()
        print("   ✅ 기본 API로 객체 생성 성공")
        
        return ('standard', cv.aruco, aruco_dict, parameters)
        
    except Exception as e:
        print(f"   ❌ 기본 API 실패: {e}")
    
    return None

def test_aruco_with_safe_method(method_info):
    """안전한 방법으로 ArUco 테스트"""
    if not method_info:
        print("사용 가능한 ArUco 방법이 없습니다")
        return False
    
    method_type, aruco_module, aruco_dict, parameters = method_info
    print(f"\n=== {method_type} 방법으로 ArUco 테스트 ===")
    
    try:
        # 카메라 열기
        cap = cv.VideoCapture(0, cv.CAP_V4L2)
        if not cap.isOpened():
            print("❌ 카메라 열기 실패")
            return False
        
        # 프레임 읽기
        ret, frame = cap.read()
        if not ret:
            print("❌ 프레임 읽기 실패")
            cap.release()
            return False
        
        # 그레이스케일 변환
        gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
        
        # ArUco 탐지 (안전한 방법)
        print("ArUco 탐지 시도...")
        
        if method_type == 'direct_import':
            corners, ids, rejected = aruco_module.detectMarkers(gray, aruco_dict, parameters=parameters)
        else:
            corners, ids, rejected = cv.aruco.detectMarkers(gray, aruco_dict, parameters=parameters)
        
        print("✅ ArUco 탐지 성공!")
        print(f"탐지된 마커 수: {len(ids) if ids is not None else 0}")
        
        # 마커 그리기 테스트
        if ids is not None and len(ids) > 0:
            print("마커 그리기 테스트...")
            if method_type == 'direct_import':
                aruco_module.drawDetectedMarkers(frame, corners, ids)
            else:
                cv.aruco.drawDetectedMarkers(frame, corners, ids)
            print("✅ 마커 그리기 성공!")
        
        # 연속 프레임 테스트
        print("연속 프레임 테스트 (10프레임)...")
        for i in range(10):
            ret, frame = cap.read()
            if not ret:
                break
            
            gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
            
            if method_type == 'direct_import':
                corners, ids, rejected = aruco_module.detectMarkers(gray, aruco_dict, parameters=parameters)
            else:
                corners, ids, rejected = cv.aruco.detectMarkers(gray, aruco_dict, parameters=parameters)
            
            if ids is not None:
                print(f"  프레임 {i+1}: {len(ids)}개 마커")
        
        print("✅ 연속 프레임 테스트 성공!")
        cap.release()
        return True
        
    except Exception as e:
        print(f"❌ {method_type} 방법 실패: {e}")
        import traceback
        traceback.print_exc()
        if 'cap' in locals():
            cap.release()
        return False

if __name__ == "__main__":
    print("ArUco 호환성 및 안정성 테스트")
    print("=" * 60)
    
    # 1. 호환성 확인
    method_info = test_opencv_aruco_compatibility()
    
    # 2. 안전한 방법으로 실제 테스트
    if method_info:
        success = test_aruco_with_safe_method(method_info)
        
        if success:
            print("\n🎉 ArUco 사용 가능!")
            print(f"권장 방법: {method_info[0]}")
            
            if method_info[0] == 'direct_import':
                print("\n사용법:")
                print("import cv2.aruco as aruco")
                print("dict_aruco = aruco.getPredefinedDictionary(aruco.DICT_5X5_250)")
                print("param_aruco = aruco.DetectorParameters()")
                print("corners, ids, rejected = aruco.detectMarkers(gray, dict_aruco, parameters=param_aruco)")
            else:
                print("\n사용법:")
                print("aruco_dict = cv.aruco.getPredefinedDictionary(cv.aruco.DICT_5X5_250)")
                print("parameters = cv.aruco.DetectorParameters()")
                print("corners, ids, rejected = cv.aruco.detectMarkers(gray, aruco_dict, parameters=parameters)")
        else:
            print("\n❌ 모든 ArUco 방법 실패")
            print("OpenCV 재빌드 또는 색상 마커 시스템 사용 권장")
    else:
        print("\n❌ ArUco 호환성 문제")
        print("OpenCV ArUco 모듈이 제대로 빌드되지 않았습니다")
