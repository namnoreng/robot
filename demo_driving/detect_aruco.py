import cv2 as cv
import numpy as np

def start_detecting_aruco(cap, marker_dict, param_markers):
    """안전한 ArUco 마커 탐지"""
    print("ArUco 마커 탐지 시작 (q로 종료)")
    
    if cap is None or not cap.isOpened():
        print("❌ 카메라가 열려있지 않습니다")
        return
    
    try:
        frame_count = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Failed to capture image")
                break
            
            frame_count += 1
            
            try:
                # 그레이스케일 변환
                gray_frame = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
                
                # ArUco 마커 탐지 (안전한 방식)
                marker_corners, marker_IDs, rejected = cv.aruco.detectMarkers(
                    gray_frame, marker_dict, parameters=param_markers
                )
                
                # 마커가 탐지된 경우
                if marker_IDs is not None and len(marker_IDs) > 0:
                    # OpenCV 내장 함수로 마커 그리기 (더 안전함)
                    cv.aruco.drawDetectedMarkers(frame, marker_corners, marker_IDs)
                    
                    # 추가 정보 표시
                    for i, marker_id in enumerate(marker_IDs):
                        # 마커 중심 계산
                        corners = marker_corners[i][0]
                        center_x = int(np.mean(corners[:, 0]))
                        center_y = int(np.mean(corners[:, 1]))
                        
                        # 중심에 정보 표시
                        cv.putText(frame, f"ID: {marker_id[0]}", 
                                 (center_x - 30, center_y), 
                                 cv.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                # 프레임 정보 표시
                cv.putText(frame, f"Frame: {frame_count}", (10, 30), 
                          cv.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                
                # 화면 표시
                cv.imshow("ArUco Detection", frame)
                
                # 키 입력 확인
                key = cv.waitKey(1) & 0xFF
                if key == ord("q") or key == 27:  # q 또는 ESC
                    print("사용자 종료")
                    break
                    
            except Exception as e:
                print(f"프레임 {frame_count} 처리 중 오류: {e}")
                continue  # 에러가 있어도 계속 진행
                
    except KeyboardInterrupt:
        print("Ctrl+C로 종료")
    except Exception as e:
        print(f"ArUco 탐지 중 전체 오류: {e}")
    finally:
        try:
            cv.destroyAllWindows()
            print("ArUco 탐지 종료")
        except:
            pass
