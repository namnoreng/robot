import cv2 as cv
import numpy as np

def test_aruco_parameter_tuning():
    """ArUco 매개변수 조정으로 Segmentation fault 해결 시도"""
    print("=== ArUco 매개변수 튜닝 테스트 ===")
    
    cap = cv.VideoCapture(0, cv.CAP_V4L2)
    if not cap.isOpened():
        print("❌ 카메라 열기 실패")
        return False
    
    ret, frame = cap.read()
    if not ret:
        print("❌ 프레임 읽기 실패")
        cap.release()
        return False
    
    gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
    
    # 여러 매개변수 조합 테스트
    parameter_sets = [
        {
            'name': '기본 설정',
            'dict': cv.aruco.DICT_5X5_250,
            'params': None
        },
        {
            'name': '작은 딕셔너리',
            'dict': cv.aruco.DICT_4X4_50,
            'params': None
        },
        {
            'name': '큰 딕셔너리',
            'dict': cv.aruco.DICT_6X6_250,
            'params': None
        },
        {
            'name': '커스텀 매개변수 1',
            'dict': cv.aruco.DICT_5X5_250,
            'params': 'custom1'
        },
        {
            'name': '커스텀 매개변수 2',
            'dict': cv.aruco.DICT_5X5_250,
            'params': 'custom2'
        }
    ]
    
    for param_set in parameter_sets:
        print(f"\n테스트 중: {param_set['name']}")
        
        try:
            # 딕셔너리 생성
            aruco_dict = cv.aruco.getPredefinedDictionary(param_set['dict'])
            
            # 매개변수 설정
            if param_set['params'] is None:
                parameters = cv.aruco.DetectorParameters()
            elif param_set['params'] == 'custom1':
                parameters = cv.aruco.DetectorParameters()
                # 더 관대한 설정
                parameters.adaptiveThreshWinSizeMin = 3
                parameters.adaptiveThreshWinSizeMax = 23
                parameters.adaptiveThreshWinSizeStep = 10
                parameters.adaptiveThreshConstant = 7
                parameters.minMarkerPerimeterRate = 0.03
                parameters.maxMarkerPerimeterRate = 4.0
            elif param_set['params'] == 'custom2':
                parameters = cv.aruco.DetectorParameters()
                # 더 엄격한 설정
                parameters.adaptiveThreshWinSizeMin = 5
                parameters.adaptiveThreshWinSizeMax = 21
                parameters.adaptiveThreshConstant = 10
                parameters.minMarkerPerimeterRate = 0.1
                parameters.maxMarkerPerimeterRate = 2.0
                parameters.polygonalApproxAccuracyRate = 0.05
            
            print(f"   딕셔너리 및 매개변수 생성 성공")
            
            # ArUco 탐지 시도
            print(f"   ArUco 탐지 시도...")
            corners, ids, rejected = cv.aruco.detectMarkers(gray, aruco_dict, parameters=parameters)
            
            print(f"✅ {param_set['name']} 성공!")
            print(f"   탐지 결과: {len(ids) if ids is not None else 0}개 마커")
            
            # 성공한 설정이면 더 테스트
            if True:  # 성공했으므로
                print(f"   추가 테스트: 5프레임 연속 처리...")
                for i in range(5):
                    ret, test_frame = cap.read()
                    if ret:
                        test_gray = cv.cvtColor(test_frame, cv.COLOR_BGR2GRAY)
                        test_corners, test_ids, test_rejected = cv.aruco.detectMarkers(
                            test_gray, aruco_dict, parameters=parameters
                        )
                        print(f"     프레임 {i+1}: {len(test_ids) if test_ids is not None else 0}개 마커")
                
                print(f"✅ {param_set['name']} 연속 처리도 성공!")
                cap.release()
                return param_set  # 성공한 설정 반환
        
        except Exception as e:
            print(f"❌ {param_set['name']} 실패: {e}")
            continue
    
    cap.release()
    return None

def test_aruco_image_preprocessing():
    """이미지 전처리로 ArUco 안정성 향상"""
    print("\n=== 이미지 전처리 ArUco 테스트 ===")
    
    cap = cv.VideoCapture(0, cv.CAP_V4L2)
    if not cap.isOpened():
        return False
    
    ret, frame = cap.read()
    if not ret:
        cap.release()
        return False
    
    preprocessing_methods = [
        {
            'name': '기본 그레이스케일',
            'method': lambda img: cv.cvtColor(img, cv.COLOR_BGR2GRAY)
        },
        {
            'name': '블러 + 그레이스케일',
            'method': lambda img: cv.cvtColor(cv.GaussianBlur(img, (5, 5), 0), cv.COLOR_BGR2GRAY)
        },
        {
            'name': '리사이즈 + 그레이스케일',
            'method': lambda img: cv.resize(cv.cvtColor(img, cv.COLOR_BGR2GRAY), (320, 240))
        },
        {
            'name': '히스토그램 평활화',
            'method': lambda img: cv.equalizeHist(cv.cvtColor(img, cv.COLOR_BGR2GRAY))
        },
        {
            'name': '적응형 임계값',
            'method': lambda img: cv.adaptiveThreshold(
                cv.cvtColor(img, cv.COLOR_BGR2GRAY), 255, 
                cv.ADAPTIVE_THRESH_GAUSSIAN_C, cv.THRESH_BINARY, 11, 2
            )
        }
    ]
    
    aruco_dict = cv.aruco.getPredefinedDictionary(cv.aruco.DICT_5X5_250)
    parameters = cv.aruco.DetectorParameters()
    
    for method in preprocessing_methods:
        print(f"\n테스트 중: {method['name']}")
        
        try:
            # 이미지 전처리
            processed = method['method'](frame)
            print(f"   전처리 완료: {processed.shape}")
            
            # ArUco 탐지
            corners, ids, rejected = cv.aruco.detectMarkers(processed, aruco_dict, parameters=parameters)
            print(f"✅ {method['name']} 성공!")
            print(f"   탐지 결과: {len(ids) if ids is not None else 0}개 마커")
            
        except Exception as e:
            print(f"❌ {method['name']} 실패: {e}")
    
    cap.release()
    return True

if __name__ == "__main__":
    print("OpenCV 버전:", cv.__version__)
    print("=" * 60)
    
    # 1. 매개변수 튜닝 테스트
    successful_params = test_aruco_parameter_tuning()
    
    if successful_params:
        print(f"\n🎉 성공한 설정: {successful_params['name']}")
        print("이 설정을 실제 코드에 적용하세요!")
    
    # 2. 이미지 전처리 테스트
    test_aruco_image_preprocessing()
    
    print("\n" + "=" * 60)
    print("권장사항:")
    if successful_params:
        print("✅ ArUco 사용 가능")
        print(f"   추천 설정: {successful_params['name']}")
        print("   이 설정을 default_setting.py에 적용하세요")
    else:
        print("❌ 모든 ArUco 설정 실패")
        print("   OpenCV 재빌드가 필요할 수 있습니다")
