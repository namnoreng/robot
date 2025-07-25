import cv2 as cv
import numpy as np

def test_aruco_step_by_step():
    """ArUco 각 단계별 테스트"""
    print("=== ArUco 단계별 테스트 ===")
    
    try:
        # 1. 카메라 열기
        print("1. 카메라 열기...")
        cap = cv.VideoCapture(0, cv.CAP_V4L2)
        if not cap.isOpened():
            print("❌ 카메라 열기 실패")
            return False
        print("✅ 카메라 열기 성공")
        
        # 2. ArUco 설정
        print("2. ArUco 설정...")
        aruco_dict = cv.aruco.getPredefinedDictionary(cv.aruco.DICT_5X5_250)
        parameters = cv.aruco.DetectorParameters()
        print("✅ ArUco 설정 성공")
        
        # 3. 프레임 읽기 테스트
        print("3. 프레임 읽기 테스트...")
        ret, frame = cap.read()
        if not ret:
            print("❌ 프레임 읽기 실패")
            return False
        print("✅ 프레임 읽기 성공")
        
        # 4. 그레이스케일 변환 테스트
        print("4. 그레이스케일 변환 테스트...")
        gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
        print("✅ 그레이스케일 변환 성공")
        
        # 5. ArUco 탐지 테스트 (가장 기본적인 방식)
        print("5. ArUco 탐지 테스트...")
        corners, ids, rejected = cv.aruco.detectMarkers(gray, aruco_dict, parameters=parameters)
        print("✅ ArUco 탐지 성공")
        print(f"   탐지된 마커 수: {len(ids) if ids is not None else 0}")
        
        # 6. 마커 그리기 테스트 (여기서 문제가 발생할 가능성이 높음)
        print("6. 마커 그리기 테스트...")
        if ids is not None and len(ids) > 0:
            print("   마커가 탐지됨 - 그리기 시도...")
            cv.aruco.drawDetectedMarkers(frame, corners, ids)
            print("✅ 마커 그리기 성공")
        else:
            print("   탐지된 마커 없음 - 그리기 건너뜀")
        
        # 7. 화면 표시 테스트
        print("7. 화면 표시 테스트...")
        cv.imshow("ArUco Step Test", frame)
        cv.waitKey(1000)  # 1초 표시
        print("✅ 화면 표시 성공")
        
        # 8. 짧은 루프 테스트 (5프레임만)
        print("8. 짧은 루프 테스트 (5프레임)...")
        for i in range(5):
            ret, frame = cap.read()
            if not ret:
                print(f"   프레임 {i+1} 읽기 실패")
                break
            
            gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
            corners, ids, rejected = cv.aruco.detectMarkers(gray, aruco_dict, parameters=parameters)
            
            # 조건부 그리기
            if ids is not None and len(ids) > 0:
                cv.aruco.drawDetectedMarkers(frame, corners, ids)
            
            cv.putText(frame, f"Frame {i+1}/5", (10, 30), 
                      cv.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            cv.imshow("ArUco Step Test", frame)
            cv.waitKey(100)  # 100ms 대기
            
            print(f"   프레임 {i+1} 처리 완료")
        
        print("✅ 짧은 루프 테스트 성공")
        
        return True
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        try:
            cap.release()
            cv.destroyAllWindows()
        except:
            pass

def test_aruco_minimal():
    """최소한의 ArUco 테스트 (화면 표시 없음)"""
    print("\n=== ArUco 최소 테스트 (화면 표시 없음) ===")
    
    try:
        cap = cv.VideoCapture(0, cv.CAP_V4L2)
        if not cap.isOpened():
            return False
        
        aruco_dict = cv.aruco.getPredefinedDictionary(cv.aruco.DICT_5X5_250)
        parameters = cv.aruco.DetectorParameters()
        
        print("10프레임 처리 중...")
        for i in range(10):
            ret, frame = cap.read()
            if not ret:
                break
            
            gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
            corners, ids, rejected = cv.aruco.detectMarkers(gray, aruco_dict, parameters=parameters)
            
            if ids is not None:
                print(f"프레임 {i+1}: {len(ids)}개 마커 탐지")
            
            # 화면 표시 없이 처리만
        
        print("✅ 최소 테스트 성공")
        return True
        
    except Exception as e:
        print(f"❌ 최소 테스트 실패: {e}")
        return False
    finally:
        try:
            cap.release()
        except:
            pass

if __name__ == "__main__":
    # 단계별 테스트
    step_success = test_aruco_step_by_step()
    
    if step_success:
        print("\n" + "="*50)
        print("단계별 테스트 성공 - 최소 테스트 진행")
        minimal_success = test_aruco_minimal()
    
    print("\n=== 최종 결과 ===")
    if step_success:
        print("✅ ArUco 기능 정상 작동")
        print("   원인: 장시간 루프나 특정 조건에서만 문제 발생")
    else:
        print("❌ ArUco 기능에 문제 있음")
        print("   조치: 대체 방법 필요")
