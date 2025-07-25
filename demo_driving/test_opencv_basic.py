import cv2 as cv
import numpy as np

def test_opencv_basic():
    """OpenCV 기본 기능 테스트"""
    print("=== OpenCV 기본 테스트 ===")
    
    try:
        # 카메라 열기
        cap = cv.VideoCapture(0, cv.CAP_V4L2)
        if not cap.isOpened():
            print("카메라 열기 실패")
            return False
        
        print("카메라 열기 성공")
        
        frame_count = 0
        print("기본 카메라 테스트 시작 (3초간, ESC로 종료)")
        
        while frame_count < 90:  # 3초간
            ret, frame = cap.read()
            if not ret:
                print("프레임 읽기 실패")
                break
            
            frame_count += 1
            
            # 간단한 처리들
            gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
            
            # 텍스트 표시
            cv.putText(frame, f"Frame: {frame_count}", (10, 30), 
                      cv.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv.putText(frame, "Basic OpenCV Test", (10, 70), 
                      cv.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
            
            # 화면 표시
            cv.imshow("OpenCV Basic Test", frame)
            
            # ESC 키 체크
            key = cv.waitKey(1) & 0xFF
            if key == 27:  # ESC
                print("ESC로 종료")
                break
        
        print("기본 테스트 완료")
        return True
        
    except Exception as e:
        print(f"기본 테스트 중 오류: {e}")
        return False
    finally:
        try:
            cap.release()
            cv.destroyAllWindows()
        except:
            pass

def test_aruco_import():
    """ArUco 모듈 import만 테스트"""
    print("\n=== ArUco 모듈 테스트 ===")
    
    try:
        print("ArUco 모듈 import 시도...")
        import cv2.aruco as aruco
        print("✅ cv2.aruco import 성공")
        
        print("ArUco 딕셔너리 생성 시도...")
        dict_aruco = cv.aruco.getPredefinedDictionary(cv.aruco.DICT_5X5_250)
        print("✅ ArUco 딕셔너리 생성 성공")
        
        print("ArUco 파라미터 생성 시도...")
        parameters = cv.aruco.DetectorParameters()
        print("✅ ArUco 파라미터 생성 성공")
        
        return True
        
    except Exception as e:
        print(f"❌ ArUco 모듈 테스트 실패: {e}")
        return False

if __name__ == "__main__":
    # 1. 기본 OpenCV 테스트
    basic_success = test_opencv_basic()
    
    # 2. ArUco 모듈 테스트 (import만)
    aruco_success = test_aruco_import()
    
    print("\n=== 결과 ===")
    print(f"기본 OpenCV: {'✅ 성공' if basic_success else '❌ 실패'}")
    print(f"ArUco 모듈: {'✅ 성공' if aruco_success else '❌ 실패'}")
    
    if basic_success and not aruco_success:
        print("\n권장사항: ArUco 없이 다른 객체 탐지 방법 사용")
    elif not basic_success:
        print("\n권장사항: OpenCV 재설치 필요")
