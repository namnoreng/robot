import cv2 as cv
import numpy as np

def test_aruco_ultra_safe():
    """ArUco 함수들을 하나씩 안전하게 테스트"""
    print("=== ArUco 초안전 테스트 ===")
    
    try:
        # 1. 카메라부터 확인
        print("1. 카메라 테스트...")
        cap = cv.VideoCapture(0, cv.CAP_V4L2)
        if not cap.isOpened():
            print("❌ 카메라 실패")
            return False
        
        ret, frame = cap.read()
        if not ret:
            print("❌ 프레임 읽기 실패")
            cap.release()
            return False
        print("✅ 카메라 정상")
        
        # 2. ArUco 딕셔너리 생성 테스트
        print("2. ArUco 딕셔너리 생성...")
        try:
            aruco_dict = cv.aruco.getPredefinedDictionary(cv.aruco.DICT_5X5_250)
            print("✅ 딕셔너리 생성 성공")
        except Exception as e:
            print(f"❌ 딕셔너리 생성 실패: {e}")
            cap.release()
            return False
        
        # 3. 파라미터 생성 테스트
        print("3. ArUco 파라미터 생성...")
        try:
            parameters = cv.aruco.DetectorParameters()
            print("✅ 파라미터 생성 성공")
        except Exception as e:
            print(f"❌ 파라미터 생성 실패: {e}")
            cap.release()
            return False
        
        # 4. 그레이스케일 변환 테스트
        print("4. 그레이스케일 변환...")
        try:
            gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
            print(f"✅ 그레이스케일 성공 (크기: {gray.shape})")
        except Exception as e:
            print(f"❌ 그레이스케일 실패: {e}")
            cap.release()
            return False
        
        # 5. 메모리 상태 확인
        print("5. 메모리 상태 확인...")
        print(f"   프레임 크기: {frame.shape}")
        print(f"   프레임 타입: {frame.dtype}")
        print(f"   그레이 크기: {gray.shape}")
        print(f"   그레이 타입: {gray.dtype}")
        
        # 6. ArUco 탐지 (가장 위험한 부분)
        print("6. ArUco 탐지 시도...")
        print("   ⚠️  여기서 Segmentation fault 발생 가능")
        
        # 추가 안전 장치
        print("   메모리 정리...")
        import gc
        gc.collect()
        
        print("   탐지 함수 호출...")
        try:
            corners, ids, rejected = cv.aruco.detectMarkers(gray, aruco_dict, parameters=parameters)
            print("✅ ArUco 탐지 성공!")
            print(f"   탐지 결과: corners={len(corners) if corners else 0}, ids={len(ids) if ids is not None else 0}")
            return True
        except Exception as e:
            print(f"❌ ArUco 탐지 실패: {e}")
            return False
        
    except Exception as e:
        print(f"❌ 전체 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        try:
            if 'cap' in locals():
                cap.release()
        except:
            pass

def test_aruco_different_dict():
    """다른 ArUco 딕셔너리로 테스트"""
    print("\n=== 다른 ArUco 딕셔너리 테스트 ===")
    
    dict_types = [
        (cv.aruco.DICT_4X4_50, "DICT_4X4_50"),
        (cv.aruco.DICT_4X4_100, "DICT_4X4_100"),
        (cv.aruco.DICT_4X4_250, "DICT_4X4_250"),
        (cv.aruco.DICT_5X5_50, "DICT_5X5_50"),
        (cv.aruco.DICT_6X6_50, "DICT_6X6_50")
    ]
    
    for dict_type, dict_name in dict_types:
        print(f"테스트 중: {dict_name}")
        try:
            aruco_dict = cv.aruco.getPredefinedDictionary(dict_type)
            parameters = cv.aruco.DetectorParameters()
            print(f"✅ {dict_name} 생성 성공")
        except Exception as e:
            print(f"❌ {dict_name} 생성 실패: {e}")

def test_aruco_small_image():
    """작은 이미지로 ArUco 테스트"""
    print("\n=== 작은 이미지 ArUco 테스트 ===")
    
    try:
        # 매우 작은 테스트 이미지 생성
        test_image = np.zeros((100, 100), dtype=np.uint8)
        test_image[20:80, 20:80] = 255  # 흰색 사각형
        
        aruco_dict = cv.aruco.getPredefinedDictionary(cv.aruco.DICT_5X5_250)
        parameters = cv.aruco.DetectorParameters()
        
        print("작은 테스트 이미지로 ArUco 탐지...")
        corners, ids, rejected = cv.aruco.detectMarkers(test_image, aruco_dict, parameters=parameters)
        print("✅ 작은 이미지 ArUco 탐지 성공")
        return True
        
    except Exception as e:
        print(f"❌ 작은 이미지 테스트 실패: {e}")
        return False

if __name__ == "__main__":
    print("OpenCV 버전:", cv.__version__)
    print("=" * 60)
    
    # 1. 다른 딕셔너리 테스트
    test_aruco_different_dict()
    
    # 2. 작은 이미지 테스트
    small_success = test_aruco_small_image()
    
    # 3. 실제 카메라 테스트 (가장 위험)
    if small_success:
        print("\n작은 이미지 성공 - 실제 카메라 테스트 진행")
        camera_success = test_aruco_ultra_safe()
    else:
        print("\n작은 이미지도 실패 - ArUco 모듈에 심각한 문제")
    
    print("\n" + "=" * 60)
    print("최종 결과:")
    if small_success:
        print("✅ ArUco 모듈 기본 기능 정상")
        if 'camera_success' in locals() and camera_success:
            print("✅ 카메라와 ArUco 조합 정상")
        else:
            print("❌ 카메라와 ArUco 조합에서 문제 발생")
    else:
        print("❌ ArUco 모듈 자체에 문제")
        print("   해결책: OpenCV 재빌드 또는 다른 버전 사용")
