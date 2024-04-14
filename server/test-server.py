from pymavlink import mavutil

def mavlink_attitude_listener():
    # Connect to the PX4 via UDP (substitute connection string as appropriate)
    drone = mavutil.mavlink_connection('/dev/ttyACM0', baud=57600)

    while True:
        # Wait for an attitude message
        attitude_msg = drone.recv_match(type='ATTITUDE', blocking=True)
        if attitude_msg:
            print(f"Roll: {attitude_msg.roll}, Pitch: {attitude_msg.pitch}, Yaw: {attitude_msg.yaw}")

        # Check for attitude target message
        attitude_target_msg = drone.recv_match(type='ATTITUDE_TARGET', blocking=True)
        if attitude_target_msg:
            print(f"Target Roll: {attitude_target_msg.body_roll_rate}, Target Pitch: {attitude_target_msg.body_pitch_rate}, Target Yaw: {attitude_target_msg.body_yaw_rate}")

if __name__ == "__main__":
    mavlink_attitude_listener()
