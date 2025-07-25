import cv2 as cv
import numpy as np

def check_aruco_build():
    """ArUco 모듈 빌드 상태 정밀 진단"""
    print("=== ArUco 빌드 상태 진단 ===")
    print(f"OpenCV 버전: {cv.__version__}")
    
    # 1. OpenCV 빌드 정보 확인
    print("\n1. OpenCV 빌드 정보:")
    build_info = cv.getBuildInformation()
    
    # ArUco 관련 빌드 옵션 검색
    aruco_keywords = [
        'BUILD_opencv_aruco',
        'opencv_contrib',
        'OPENCV_EXTRA_MODULES_PATH',
        'aruco'
    ]
    
    for keyword in aruco_keywords:
        if keyword in build_info:
            lines = build_info.split('\n')
            for line in lines:
                if keyword in line:
                    print(f"   {line.strip()}")
        else:
            print(f"   ❌ {keyword} 정보 없음")
    
    # 2. ArUco 모듈 속성 상세 확인
    print("\n2. ArUco 모듈 내부 구조:")
    try:
        import cv2.aruco as aruco_module
        print("   ✅ cv2.aruco 모듈 import 성공")
        
        # 중요 함수들의 실제 바인딩 확인
        critical_functions = [
            'getPredefinedDictionary',
            'DetectorParameters', 
            'detectMarkers',
            'drawDetectedMarkers'
        ]
        
        for func_name in critical_functions:
            if hasattr(aruco_module, func_name):
                func_obj = getattr(aruco_module, func_name)
                print(f"   ✅ {func_name}: {type(func_obj)}")
            else:
                print(f"   ❌ {func_name}: 없음")
        
        # 3. 딕셔너리 생성 테스트 (안전)
        print("\n3. 딕셔너리 생성 테스트:")
        try:
            dict_aruco = aruco_module.getPredefinedDictionary(aruco_module.DICT_5X5_250)
            print(f"   ✅ 딕셔너리 생성 성공: {type(dict_aruco)}")
            
            # 딕셔너리 속성 확인
            if hasattr(dict_aruco, 'markerSize'):
                print(f"   - markerSize: {dict_aruco.markerSize}")
            if hasattr(dict_aruco, 'maxCorrectionBits'):
                print(f"   - maxCorrectionBits: {dict_aruco.maxCorrectionBits}")
                
        except Exception as e:
            print(f"   ❌ 딕셔너리 생성 실패: {e}")
            return False
        
        # 4. 파라미터 생성 테스트 (안전)
        print("\n4. 파라미터 생성 테스트:")
        try:
            params = aruco_module.DetectorParameters()
            print(f"   ✅ 파라미터 생성 성공: {type(params)}")
            
            # 파라미터 속성 확인
            if hasattr(params, 'adaptiveThreshWinSizeMin'):
                print(f"   - adaptiveThreshWinSizeMin: {params.adaptiveThreshWinSizeMin}")
                
        except Exception as e:
            print(f"   ❌ 파라미터 생성 실패: {e}")
            return False
        
        # 5. 더미 이미지로 detectMarkers 테스트 (위험!)
        print("\n5. 더미 이미지 detectMarkers 테스트:")
        print("   ⚠️  여기서 Segmentation fault 발생 가능!")
        
        try:
            # 작은 더미 이미지 생성
            dummy_img = np.zeros((50, 50), dtype=np.uint8)
            dummy_img[10:40, 10:40] = 255
            
            print("   더미 이미지 생성 완료")
            print("   detectMarkers 호출 시도...")
            
            # 위험한 함수 호출
            corners, ids, rejected = aruco_module.detectMarkers(dummy_img, dict_aruco, parameters=params)
            
            print("   ✅ detectMarkers 성공!")
            print(f"   결과: corners={len(corners)}, ids={ids is not None}")
            return True
            
        except Exception as e:
            print(f"   ❌ detectMarkers 실패: {e}")
            return False
    
    except Exception as e:
        print(f"❌ ArUco 모듈 전체 실패: {e}")
        return False

def check_opencv_modules():
    """OpenCV 모듈 전체 확인"""
    print("\n=== OpenCV 모듈 확인 ===")
    
    # 사용 가능한 모듈 목록
    available_modules = []
    
    module_names = [
        'aruco', 'calib3d', 'core', 'dnn', 'features2d', 
        'flann', 'highgui', 'imgcodecs', 'imgproc', 
        'ml', 'objdetect', 'photo', 'stitching', 
        'video', 'videoio'
    ]
    
    for module in module_names:
        if hasattr(cv, module):
            available_modules.append(module)
            print(f"   ✅ {module}")
        else:
            print(f"   ❌ {module}")
    
    print(f"\n사용 가능한 모듈: {len(available_modules)}/{len(module_names)}")
    
    if 'aruco' not in available_modules:
        print("🚨 ArUco 모듈이 없습니다! OpenCV가 opencv_contrib 없이 빌드됨")
        return False
    
    return True

if __name__ == "__main__":
    print("OpenCV ArUco 빌드 상태 정밀 진단")
    print("=" * 60)
    
    # 1. 기본 모듈 확인
    modules_ok = check_opencv_modules()
    
    if not modules_ok:
        print("\n🚨 OpenCV 재빌드 필요 (opencv_contrib 포함)")
        print("   cmake -D OPENCV_EXTRA_MODULES_PATH=<opencv_contrib>/modules ..")
        exit(1)
    
    # 2. ArUco 상세 진단
    aruco_ok = check_aruco_build()
    
    print("\n" + "=" * 60)
    print("최종 진단 결과:")
    
    if aruco_ok:
        print("✅ ArUco 모듈 정상 - 다른 원인일 가능성")
        print("   - 카메라/UI 문제 확인 필요")
        print("   - GTK/OpenGL 빌드 옵션 문제일 수 있음")
    else:
        print("🚨 ArUco 모듈에 문제 - 재빌드 필요")
        print("   - opencv_contrib의 ArUco 모듈이 제대로 빌드되지 않음")
        print("   - BUILD_opencv_aruco=ON 확인 필요")
