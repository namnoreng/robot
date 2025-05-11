import os
import subprocess
from pymycobot.myagv import MyAgv

def kill_ros_nodes():
    """
    Kill all running ROS nodes.
    """
    try:
        # Get list of all running nodes
        result = subprocess.run(["rosnode", "list"], capture_output=True, text=True)
        nodes = result.stdout.strip().split("\n")

        if nodes:
            print(f"Found nodes: {nodes}")
            for node in nodes:
                print(f"Killing node: {node}")
                subprocess.run(["rosnode", "kill", node])
        else:
            print("No ROS nodes are currently running.")
    except Exception as e:
        print(f"Error while killing ROS nodes: {e}")

def kill_ros_processes():
    """
    Kill all running ROS-related processes.
    """
    try:
        # Kill ROS processes like rosmaster, rosout
        print("Killing ROS-related processes...")
        subprocess.run(["killall", "-9", "rosmaster", "rosout", "python3"])
        print("ROS processes terminated.")
    except Exception as e:
        print(f"Error while killing ROS processes: {e}")

def reset_agv():
    """
    Reset AGV state by stopping it and initializing.
    """
    try:
        agv = MyAgv("/dev/ttyAMA2", 115200)
        agv.stop()
        print("AGV has been stopped and reset.")
    except Exception as e:
        print(f"Error while resetting AGV: {e}")

def cleanup_environment():
    """
    Clean up the ROS environment and reset state.
    """
    print("Starting environment cleanup...")
    kill_ros_nodes()
    kill_ros_processes()
    reset_agv()
    print("Environment cleanup complete. System is reset.")

if __name__ == "__main__":
    cleanup_environment()
