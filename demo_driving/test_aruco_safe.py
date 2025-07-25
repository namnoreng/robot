import cv2 as cv
import numpy as np

def test_aruco_simple():
    """간단한 ArUco 테스트"""
    print("=== ArUco 간단 테스트 ===")
    
    try:
        # 카메라 열기
        cap = cv.VideoCapture(0, cv.CAP_V4L2)
        if not cap.isOpened():
            print("카메라 열기 실패")
            return False
        
        print("카메라 열기 성공")
        
        # ArUco 설정 (가장 안전한 방식)
        print("ArUco 설정 중...")
        try:
            aruco_dict = cv.aruco.getPredefinedDictionary(cv.aruco.DICT_5X5_250)
            print("ArUco 딕셔너리 생성 성공")
        except Exception as e:
            print(f"ArUco 딕셔너리 생성 실패: {e}")
            return False
        
        try:
            parameters = cv.aruco.DetectorParameters()
            print("ArUco 파라미터 생성 성공")
        except Exception as e:
            print(f"ArUco 파라미터 생성 실패: {e}")
            return False
        
        frame_count = 0
        print("ArUco 탐지 시작 (5초간 테스트, ESC로 조기 종료)")
        
        while frame_count < 150:  # 5초간 (30fps 기준)
            ret, frame = cap.read()
            if not ret:
                print("프레임 읽기 실패")
                break
            
            frame_count += 1
            
            try:
                # 그레이스케일 변환
                gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
                
                # ArUco 마커 탐지 (가장 기본적인 방식)
                corners, ids, rejected = cv.aruco.detectMarkers(gray, aruco_dict, parameters=parameters)
                
                # 마커가 탐지되면 표시
                if ids is not None:
                    # 마커 경계 그리기
                    cv.aruco.drawDetectedMarkers(frame, corners, ids)
                    print(f"프레임 {frame_count}: {len(ids)}개 마커 탐지됨 - IDs: {ids.flatten()}")
                
                # 프레임 표시
                cv.imshow("ArUco Test", frame)
                
                # ESC 키 체크
                key = cv.waitKey(1) & 0xFF
                if key == 27:  # ESC
                    print("ESC로 종료")
                    break
                    
            except Exception as e:
                print(f"프레임 {frame_count} 처리 중 오류: {e}")
                break
        
        print("테스트 완료")
        return True
        
    except Exception as e:
        print(f"전체 테스트 중 오류: {e}")
        return False
    finally:
        try:
            cap.release()
            cv.destroyAllWindows()
        except:
            pass

if __name__ == "__main__":
    success = test_aruco_simple()
    if success:
        print("✅ ArUco 테스트 성공")
    else:
        print("❌ ArUco 테스트 실패")
