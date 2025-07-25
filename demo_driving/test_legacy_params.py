import cv2 as cv
import numpy as np
from cv2 import aruco

def test_legacy_detector_parameters():
    """레거시 DetectorParameters_create() 테스트"""
    print("=== 레거시 DetectorParameters_create() 테스트 ===")
    
    try:
        # 카메라 열기
        cap = cv.VideoCapture(0, cv.CAP_V4L2)
        if not cap.isOpened():
            print("❌ 카메라 열기 실패")
            return False
        
        # ArUco 딕셔너리 생성
        aruco_dict = cv.aruco.getPredefinedDictionary(cv.aruco.DICT_5X5_250)
        print("✅ ArUco 딕셔너리 생성 성공")
        
        # 방법 1: OpenCV 3.x 스타일 (legacy)
        print("\n1. aruco.DetectorParameters_create() 시도...")
        try:
            param_legacy = aruco.DetectorParameters_create()
            print("✅ DetectorParameters_create() 성공!")
            print(f"   타입: {type(param_legacy)}")
            
            # 속성 접근 테스트
            try:
                print(f"   adaptiveThreshWinSizeMin: {param_legacy.adaptiveThreshWinSizeMin}")
                print("✅ 속성 접근 성공")
            except Exception as e:
                print(f"❌ 속성 접근 실패: {e}")
                
        except Exception as e:
            print(f"❌ DetectorParameters_create() 실패: {e}")
            param_legacy = None
        
        # 방법 2: cv.aruco.DetectorParameters_create() 시도
        print("\n2. cv.aruco.DetectorParameters_create() 시도...")
        try:
            param_cv_legacy = cv.aruco.DetectorParameters_create()
            print("✅ cv.aruco.DetectorParameters_create() 성공!")
            print(f"   타입: {type(param_cv_legacy)}")
        except Exception as e:
            print(f"❌ cv.aruco.DetectorParameters_create() 실패: {e}")
            param_cv_legacy = None
        
        # 방법 3: 강제로 OpenCV 3.x 방식 사용
        print("\n3. 강제 OpenCV 3.x 방식 시도...")
        try:
            dict_legacy = aruco.Dictionary_get(aruco.DICT_5X5_250)
            param_force_legacy = aruco.DetectorParameters_create()
            print("✅ 강제 레거시 방식 성공!")
            print(f"   딕셔너리 타입: {type(dict_legacy)}")
            print(f"   파라미터 타입: {type(param_force_legacy)}")
        except Exception as e:
            print(f"❌ 강제 레거시 방식 실패: {e}")
            dict_legacy = None
            param_force_legacy = None
        
        # 실제 ArUco 탐지 테스트
        print("\n4. 실제 ArUco 탐지 테스트...")
        
        ret, frame = cap.read()
        if not ret:
            print("❌ 프레임 읽기 실패")
            cap.release()
            return False
        
        gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
        
        # 테스트할 파라미터들
        test_params = [
            ("legacy aruco.DetectorParameters_create()", param_legacy),
            ("cv.aruco.DetectorParameters_create()", param_cv_legacy),
            ("force legacy", param_force_legacy)
        ]
        
        for name, params in test_params:
            if params is not None:
                print(f"\n   {name} 테스트...")
                try:
                    if name == "force legacy" and dict_legacy is not None:
                        # 완전 레거시 방식
                        corners, ids, rejected = aruco.detectMarkers(gray, dict_legacy, parameters=params)
                    else:
                        # 일반적인 방식
                        corners, ids, rejected = cv.aruco.detectMarkers(gray, aruco_dict, parameters=params)
                    
                    print(f"   ✅ {name} ArUco 탐지 성공!")
                    print(f"      탐지된 마커: {len(ids) if ids is not None else 0}개")
                    
                    # 연속 테스트
                    print(f"   연속 5프레임 테스트...")
                    for i in range(5):
                        ret, test_frame = cap.read()
                        if ret:
                            test_gray = cv.cvtColor(test_frame, cv.COLOR_BGR2GRAY)
                            if name == "force legacy" and dict_legacy is not None:
                                test_corners, test_ids, test_rejected = aruco.detectMarkers(
                                    test_gray, dict_legacy, parameters=params
                                )
                            else:
                                test_corners, test_ids, test_rejected = cv.aruco.detectMarkers(
                                    test_gray, aruco_dict, parameters=params
                                )
                            print(f"     프레임 {i+1}: {len(test_ids) if test_ids is not None else 0}개")
                    
                    print(f"   ✅ {name} 연속 테스트 성공!")
                    cap.release()
                    return (name, params, dict_legacy if name == "force legacy" else aruco_dict)
                    
                except Exception as e:
                    print(f"   ❌ {name} ArUco 탐지 실패: {e}")
                    continue
        
        cap.release()
        return None
        
    except Exception as e:
        print(f"❌ 전체 테스트 실패: {e}")
        if 'cap' in locals():
            cap.release()
        return False

if __name__ == "__main__":
    print("ArUco DetectorParameters_create() 테스트")
    print("=" * 60)
    
    result = test_legacy_detector_parameters()
    
    print("\n" + "=" * 60)
    print("최종 결과:")
    
    if result and len(result) == 3:
        method_name, params, dict_obj = result
        print(f"✅ 성공한 방법: {method_name}")
        print(f"   파라미터 타입: {type(params)}")
        print(f"   딕셔너리 타입: {type(dict_obj)}")
        
        print("\n적용 방법:")
        if method_name == "force legacy":
            print("# default_setting.py에서 사용:")
            print("from cv2 import aruco")
            print("marker_dict = aruco.Dictionary_get(aruco.DICT_5X5_250)")
            print("param_markers = aruco.DetectorParameters_create()")
            print("")
            print("# detect_aruco.py에서 사용:")
            print("corners, ids, rejected = aruco.detectMarkers(gray, marker_dict, parameters=param_markers)")
        elif "cv.aruco" in method_name:
            print("# default_setting.py에서 사용:")
            print("marker_dict = cv.aruco.getPredefinedDictionary(cv.aruco.DICT_5X5_250)")
            print("param_markers = cv.aruco.DetectorParameters_create()")
        else:
            print("# default_setting.py에서 사용:")
            print("from cv2 import aruco")
            print("marker_dict = cv.aruco.getPredefinedDictionary(cv.aruco.DICT_5X5_250)")
            print("param_markers = aruco.DetectorParameters_create()")
        
    elif result is False:
        print("❌ 모든 DetectorParameters_create() 방법 실패")
        print("   파라미터 없이 사용하는 것이 최선")
    else:
        print("❌ ArUco 탐지 자체에 문제")
        print("   파라미터 없는 방식 사용 권장")
