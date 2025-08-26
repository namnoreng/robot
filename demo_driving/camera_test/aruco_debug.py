#!/usr/bin/env python3
"""
CSI 카메라 ArUco 마커 인식 디버깅 도구
마커 인식이 안 될 때 문제를 찾고 해결하는 도구
"""
import cv2 as cv
import numpy as np
import time
from cv2 import aruco

def gstreamer_pipeline(capture_width=640, capture_height=480, 
                      display_width=640, display_height=480, 
                      framerate=30, flip_method=0):
    """간단한 CSI 카메라 파이프라인"""
    return (
        "nvarguscamerasrc ! "
        "video/x-raw(memory:NVMM), "
        f"width={capture_width}, height={capture_height}, framerate={framerate}/1 ! "
        "nvvidconv flip-method=" + str(flip_method) + " ! "
        f"video/x-raw, width={display_width}, height={display_height}, format=BGRx ! "
        "videoconvert ! "
        "video/x-raw, format=BGR ! appsink max-buffers=1 drop=true"
    )

def test_aruco_dictionaries():
    """다양한 ArUco 딕셔너리 테스트"""
    print("=== ArUco 딕셔너리 테스트 ===")
    
    dictionaries = [
        (cv.aruco.DICT_4X4_50, "DICT_4X4_50"),
        (cv.aruco.DICT_4X4_100, "DICT_4X4_100"), 
        (cv.aruco.DICT_4X4_250, "DICT_4X4_250"),
        (cv.aruco.DICT_5X5_50, "DICT_5X5_50"),
        (cv.aruco.DICT_5X5_100, "DICT_5X5_100"),
        (cv.aruco.DICT_5X5_250, "DICT_5X5_250"),
        (cv.aruco.DICT_6X6_50, "DICT_6X6_50"),
        (cv.aruco.DICT_6X6_100, "DICT_6X6_100"),
        (cv.aruco.DICT_6X6_250, "DICT_6X6_250"),
    ]
    
    # CSI 카메라 초기화
    pipeline = gstreamer_pipeline()
    cap = cv.VideoCapture(pipeline, cv.CAP_GSTREAMER)
    
    if not cap.isOpened():
        print("❌ CSI 카메라 열기 실패")
        return
    
    print("📹 CSI 카메라 성공 - 각 딕셔너리로 검출 테스트")
    print("SPACE: 다음 딕셔너리, ESC: 종료")
    
    dict_index = 0
    
    while dict_index < len(dictionaries):
        dict_id, dict_name = dictionaries[dict_index]
        aruco_dict = cv.aruco.Dictionary_get(dict_id)
        parameters = cv.aruco.DetectorParameters_create()
        
        print(f"\n🎯 테스트 중: {dict_name}")
        
        # 5초간 각 딕셔너리로 테스트
        start_time = time.time()
        detection_count = 0
        frame_count = 0
        
        while time.time() - start_time < 5:
            ret, frame = cap.read()
            if not ret:
                continue
            
            frame_count += 1
            
            # ArUco 검출
            gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
            corners, ids, _ = cv.aruco.detectMarkers(gray, aruco_dict, parameters=parameters)
            
            if ids is not None:
                detection_count += 1
                cv.aruco.drawDetectedMarkers(frame, corners, ids)
                
                for i, marker_id in enumerate(ids):
                    center = np.mean(corners[i][0], axis=0).astype(int)
                    cv.putText(frame, f"ID: {marker_id[0]}", 
                              (center[0] - 30, center[1] - 10), 
                              cv.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            
            # 정보 표시
            cv.putText(frame, f"Dictionary: {dict_name}", (10, 30), 
                      cv.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv.putText(frame, f"Detections: {detection_count}/{frame_count}", (10, 60), 
                      cv.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            
            cv.imshow('ArUco Dictionary Test', frame)
            
            key = cv.waitKey(1) & 0xFF
            if key == 27:  # ESC
                cap.release()
                cv.destroyAllWindows()
                return
            elif key == ord(' '):  # SPACE
                break
        
        if detection_count > 0:
            detection_rate = (detection_count / frame_count) * 100
            print(f"✅ {dict_name}: {detection_count}회 검출 ({detection_rate:.1f}%)")
        else:
            print(f"❌ {dict_name}: 검출 실패")
        
        dict_index += 1
    
    cap.release()
    cv.destroyAllWindows()

def test_image_preprocessing():
    """이미지 전처리별 ArUco 검출 테스트"""
    print("\n=== 이미지 전처리 테스트 ===")
    
    # 가장 일반적인 딕셔너리 사용
    aruco_dict = cv.aruco.Dictionary_get(cv.aruco.DICT_6X6_250)
    parameters = cv.aruco.DetectorParameters_create()
    
    pipeline = gstreamer_pipeline()
    cap = cv.VideoCapture(pipeline, cv.CAP_GSTREAMER)
    
    if not cap.isOpened():
        print("❌ CSI 카메라 열기 실패")
        return
    
    print("📹 다양한 전처리 방법으로 검출 테스트")
    print("SPACE: 다음 전처리, ESC: 종료")
    
    preprocessing_methods = [
        ("원본", lambda img: img),
        ("밝기+50", lambda img: cv.convertScaleAbs(img, alpha=1.0, beta=50)),
        ("밝기-50", lambda img: cv.convertScaleAbs(img, alpha=1.0, beta=-50)),
        ("대비 증가", lambda img: cv.convertScaleAbs(img, alpha=1.5, beta=0)),
        ("대비 감소", lambda img: cv.convertScaleAbs(img, alpha=0.7, beta=0)),
        ("가우시안 블러", lambda img: cv.GaussianBlur(img, (5, 5), 0)),
        ("히스토그램 평활화", lambda img: cv.equalizeHist(img)),
        ("CLAHE", lambda img: cv.createCLAHE(clipLimit=2.0, tileGridSize=(8,8)).apply(img)),
        ("이진화", lambda img: cv.threshold(img, 127, 255, cv.THRESH_BINARY)[1]),
        ("적응적 이진화", lambda img: cv.adaptiveThreshold(img, 255, cv.ADAPTIVE_THRESH_GAUSSIAN_C, cv.THRESH_BINARY, 11, 2)),
    ]
    
    method_index = 0
    
    while method_index < len(preprocessing_methods):
        method_name, preprocess_func = preprocessing_methods[method_index]
        
        print(f"\n🔧 테스트 중: {method_name}")
        
        # 3초간 테스트
        start_time = time.time()
        detection_count = 0
        frame_count = 0
        
        while time.time() - start_time < 3:
            ret, frame = cap.read()
            if not ret:
                continue
            
            frame_count += 1
            
            # 그레이스케일 변환
            gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
            
            # 전처리 적용
            processed = preprocess_func(gray)
            
            # ArUco 검출
            corners, ids, _ = cv.aruco.detectMarkers(processed, aruco_dict, parameters=parameters)
            
            if ids is not None:
                detection_count += 1
                cv.aruco.drawDetectedMarkers(frame, corners, ids)
            
            # 전처리된 이미지를 컬러로 변환해서 표시
            if len(processed.shape) == 2:
                processed_display = cv.cvtColor(processed, cv.COLOR_GRAY2BGR)
            else:
                processed_display = processed
            
            # 원본과 전처리 이미지를 나란히 표시
            combined = np.hstack([frame, processed_display])
            
            cv.putText(combined, f"Method: {method_name}", (10, 30), 
                      cv.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv.putText(combined, f"Detections: {detection_count}/{frame_count}", (10, 60), 
                      cv.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            
            cv.imshow('Preprocessing Test', combined)
            
            key = cv.waitKey(1) & 0xFF
            if key == 27:  # ESC
                cap.release()
                cv.destroyAllWindows()
                return
            elif key == ord(' '):  # SPACE
                break
        
        if detection_count > 0:
            detection_rate = (detection_count / frame_count) * 100
            print(f"✅ {method_name}: {detection_count}회 검출 ({detection_rate:.1f}%)")
        else:
            print(f"❌ {method_name}: 검출 실패")
        
        method_index += 1
    
    cap.release()
    cv.destroyAllWindows()

def test_aruco_parameters():
    """ArUco 검출 파라미터 최적화 테스트"""
    print("\n=== ArUco 파라미터 테스트 ===")
    
    aruco_dict = cv.aruco.Dictionary_get(cv.aruco.DICT_6X6_250)
    
    pipeline = gstreamer_pipeline()
    cap = cv.VideoCapture(pipeline, cv.CAP_GSTREAMER)
    
    if not cap.isOpened():
        print("❌ CSI 카메라 열기 실패")
        return
    
    parameter_sets = [
        ("기본 설정", {}),
        ("관대한 설정", {
            'minMarkerPerimeterRate': 0.01,
            'maxMarkerPerimeterRate': 8.0,
            'polygonalApproxAccuracyRate': 0.05,
            'minCornerDistanceRate': 0.01,
            'minDistanceToBorder': 1
        }),
        ("엄격한 설정", {
            'minMarkerPerimeterRate': 0.05,
            'maxMarkerPerimeterRate': 2.0,
            'polygonalApproxAccuracyRate': 0.01,
            'minCornerDistanceRate': 0.1,
            'minDistanceToBorder': 5
        }),
        ("적응적 임계값 조정", {
            'adaptiveThreshWinSizeMin': 5,
            'adaptiveThreshWinSizeMax': 15,
            'adaptiveThreshWinSizeStep': 5,
            'adaptiveThreshConstant': 10
        }),
        ("코너 정제 설정", {
            'cornerRefinementMethod': cv.aruco.CORNER_REFINE_SUBPIX,
            'cornerRefinementWinSize': 3,
            'cornerRefinementMaxIterations': 50,
            'cornerRefinementMinAccuracy': 0.05
        })
    ]
    
    print("SPACE: 다음 파라미터 세트, ESC: 종료")
    
    param_index = 0
    
    while param_index < len(parameter_sets):
        param_name, param_dict = parameter_sets[param_index]
        
        # 파라미터 설정
        parameters = cv.aruco.DetectorParameters_create()
        for key, value in param_dict.items():
            setattr(parameters, key, value)
        
        print(f"\n⚙️ 테스트 중: {param_name}")
        
        # 3초간 테스트
        start_time = time.time()
        detection_count = 0
        frame_count = 0
        
        while time.time() - start_time < 3:
            ret, frame = cap.read()
            if not ret:
                continue
            
            frame_count += 1
            
            gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
            corners, ids, _ = cv.aruco.detectMarkers(gray, aruco_dict, parameters=parameters)
            
            if ids is not None:
                detection_count += 1
                cv.aruco.drawDetectedMarkers(frame, corners, ids)
            
            cv.putText(frame, f"Parameters: {param_name}", (10, 30), 
                      cv.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv.putText(frame, f"Detections: {detection_count}/{frame_count}", (10, 60), 
                      cv.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            
            cv.imshow('Parameter Test', frame)
            
            key = cv.waitKey(1) & 0xFF
            if key == 27:  # ESC
                cap.release()
                cv.destroyAllWindows()
                return
            elif key == ord(' '):  # SPACE
                break
        
        if detection_count > 0:
            detection_rate = (detection_count / frame_count) * 100
            print(f"✅ {param_name}: {detection_count}회 검출 ({detection_rate:.1f}%)")
        else:
            print(f"❌ {param_name}: 검출 실패")
        
        param_index += 1
    
    cap.release()
    cv.destroyAllWindows()

def create_test_marker():
    """테스트용 ArUco 마커 생성"""
    print("\n=== ArUco 마커 생성 ===")
    
    dictionaries = [
        (cv.aruco.DICT_4X4_50, "4x4_50"),
        (cv.aruco.DICT_5X5_250, "5x5_250"),
        (cv.aruco.DICT_6X6_250, "6x6_250"),
    ]
    
    for dict_id, dict_name in dictionaries:
        aruco_dict = cv.aruco.Dictionary_get(dict_id)
        
        for marker_id in [0, 1, 2, 3, 4]:
            # 200x200 픽셀 마커 생성
            marker_image = cv.aruco.drawMarker(aruco_dict, marker_id, 200)
            
            filename = f"test_marker_{dict_name}_id{marker_id}.png"
            cv.imwrite(filename, marker_image)
            print(f"📄 생성: {filename}")
    
    print("\n💡 생성된 마커를 프린터로 출력하거나 화면에 표시해서 테스트하세요!")

def diagnose_aruco_issues():
    """ArUco 인식 문제 종합 진단"""
    print("=== CSI 카메라 ArUco 인식 문제 진단 도구 ===")
    print("")
    print("1. ArUco 딕셔너리 테스트")
    print("2. 이미지 전처리 테스트") 
    print("3. ArUco 파라미터 테스트")
    print("4. 테스트 마커 생성")
    print("5. 전체 진단 실행")
    
    choice = input("\n선택하세요 (1-5): ").strip()
    
    if choice == "1":
        test_aruco_dictionaries()
    elif choice == "2":
        test_image_preprocessing()
    elif choice == "3":
        test_aruco_parameters()
    elif choice == "4":
        create_test_marker()
    elif choice == "5":
        print("📋 전체 진단을 시작합니다...")
        create_test_marker()
        test_aruco_dictionaries()
        test_image_preprocessing() 
        test_aruco_parameters()
        print("\n✅ 전체 진단 완료!")
    else:
        print("전체 진단을 실행합니다.")
        create_test_marker()
        test_aruco_dictionaries()
        test_image_preprocessing()
        test_aruco_parameters()

if __name__ == "__main__":
    diagnose_aruco_issues()
