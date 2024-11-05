import argparse
import os
import sys
import signal
import time
from sensor import Sensor

# Global variables
robots = {}
positions = {}
pipes = {}
treasures_found = []

# Signal handlers for master process
def sigint_handler(sig, frame):
    print("\nReceived SIGINT. Shutting down.")
    shutdown_robots()

def sigquit_handler(sig, frame):
    print("Sending SIGUSR1 to replenish battery for all robots.")
    for pid in robots.values():
        os.kill(pid, signal.SIGUSR1)  # Send SIGUSR1 to each robot

def sigtstp_handler(sig, frame):
    print("Sending SIGTSTP to request status from all robots.")
    for pid in robots.values():
        os.kill(pid, signal.SIGTSTP)  # Send SIGTSTP to each robot

def shutdown_robots():
    final_status = {}  # Dictionary to store final position and battery for each robot

    # Send 'exit' command to each robot to request last status and initiate shutdown
    for robot_id, (parent_to_child_w, child_to_parent_r) in pipes.items():
        # Write 'exit' command to the child process
        os.write(parent_to_child_w, b"exit\n")
        
        # Read and store the final position and battery from each robot
        response = os.read(child_to_parent_r, 1024).decode().strip()
        final_status[robot_id] = response
        _, status = os.waitpid(robots[robot_id], 0)  # Wait for each child process to exit
        print(f"Robot {robots[robot_id]} finished with status {status}")


    # Print each robot's final message (position and battery) from final_status
    for robot_id, response in final_status.items():
        pid = robots[robot_id]
        print(f"Robot {robot_id} pid: {robots[robot_id]} last message:")
        print(response)
        print()

    # Final message on treasures found or missed
    print("All treasures found!" if len(treasures_found) == SENSOR.n_treasures() else "Some treasures remain undiscovered.")
    sys.exit(0)


def start_robot(robot_id, position, battery, filename):
    # Create two pipes for bidirectional communication
    child_from_parent, parent_to_child = os.pipe()  # Parent-to-Child pipe
    parent_from_child, child_to_parent = os.pipe()  # Child-to-Parent pipe

    pid = os.fork()

    if pid == 0:  # Child process
        # Close unused ends of pipes in the child process
        os.close(parent_to_child)       # Close parent's write end in child
        os.close(parent_from_child)     # Close parent's read end in child

        # Redirect child's stdin to read end of Parent-to-Child pipe
        os.dup2(child_from_parent, sys.stdin.fileno())

        # Redirect child's stdout to write end of Child-to-Parent pipe
        os.dup2(child_to_parent, sys.stdout.fileno())

        # Close the original file descriptors after redirection
        os.close(child_from_parent)
        os.close(child_to_parent)

        # Execute robot.py as the child process
        os.execvp("python3", ["python3", "robot.py", str(robot_id), "-f", filename, "-pos", str(position[0]), str(position[1]), "-b", str(battery)])
        sys.exit(0)

    else:  # Parent process
        # Parent process: close unused ends of pipes
        os.close(child_from_parent)  # Close child’s read end in parent
        os.close(child_to_parent)    # Close child’s write end in parent

        print(f'Robot {robot_id} PID: {pid} Position: {position}')

        # Store file descriptors for further communication
        pipes[robot_id] = (parent_to_child, parent_from_child)  # (write to child, read from child)
        positions[robot_id] = position
        robots[robot_id] = pid


# Function to send move command and handle responses for mv <robot_id/all> <direction>
def move_robot(robot_id, direction):
    # Get the write and read ends of the pipes for the robot
    child_from_parent, child_to_parent = pipes[robot_id]
    
    # Write the move command to the child
    os.write(child_from_parent, f"mv {direction}\n".encode())
    
    # Read the response from the child
    response = os.read(child_to_parent, 1024).decode().strip()

    # Process the response
    if "Treasure" in response:
        print(response)  # Print if the robot finds a treasure
        treasures_found.append(positions[robot_id])  # Track the found treasure's position
    elif "Collision" in response:
        print(response)  # Print if there's a collision
    elif "OK" in response:
        # Update position based on robot response if movement was successful
        new_position = calculate_new_position(positions[robot_id], direction)
        positions[robot_id] = new_position
        print(f"Robot {robot_id} status: OK; {direction} to {new_position}")
    elif "KO" in response:
        print(f"Robot {robot_id} cannot move {direction}")

def calculate_new_position(current_position, direction):
    if direction == "up":
        return (current_position[0] - 1, current_position[1])
    elif direction == "down":
        return (current_position[0] + 1, current_position[1])
    elif direction == "left":
        return (current_position[0], current_position[1] - 1)
    elif direction == "right":
        return (current_position[0], current_position[1] + 1)
    else:
        print(f"Invalid direction: {direction}")
        return current_position

if __name__ == "__main__":
    # Argument parsing
    parser = argparse.ArgumentParser()
    parser.add_argument('-room', '--room_filename')
    parser.add_argument('-robots', '--robots_filename')
    args = parser.parse_args()

    ROOM_FILENAME = args.room_filename
    ROBOTS_FILENAME = args.robots_filename

    # Initialize Sensor
    SENSOR = Sensor(ROOM_FILENAME)
    num_treasures = SENSOR.n_treasures()
    room_dimensions = SENSOR.dimensions()

    # Signal handling setup for master process
    signal.signal(signal.SIGINT, sigint_handler)
    signal.signal(signal.SIGQUIT, sigquit_handler)
    signal.signal(signal.SIGTSTP, sigtstp_handler)

    # Read robot positions from file and start each robot as a child process
    with open(ROBOTS_FILENAME, 'r') as robot_file:
        for robot_id, line in enumerate(robot_file, start=1):
            pos = tuple(map(int, line.strip().strip("()").split(',')))
            if not SENSOR.with_obstacle(pos[0], pos[1]):
                print(f"Invalid initial position for robot at {pos}")
                sys.exit(1)
            start_robot(robot_id, pos, 100, ROOM_FILENAME)


    # Command loop for user input
    while True:
        action = input("Command: ").strip().split()
        command = action[0]

        if command == "mv":
            target, direction = action[1], action[2]
            if target == "all":
                for robot_id in sorted(robots):  # Move each robot sequentially
                    move_robot(robot_id, direction)
            else:
                robot_id = int(target)
                if robot_id in pipes:
                    move_robot(robot_id, direction)
                else:
                    print(f"No robot with id {robot_id}")

        elif command == "bat":
            target = action[1]
            if target == "all":
                for robot_id, parent_conn in pipes.items():
                    os.write(parent_conn, b"bat\n")
            else:
                robot_id = int(target)
                if robot_id in pipes:
                    parent_conn = pipes[robot_id]
                    os.write(parent_conn, b"bat\n")
                else:
                    print(f"No robot with id {robot_id}")

        elif command == "pos":
            target = action[1]
            if target == "all":
                for robot_id, parent_conn in pipes.items():
                    os.write(parent_conn, b"pos\n")
            else:
                robot_id = int(target)
                if robot_id in pipes:
                    parent_conn = pipes[robot_id]
                    os.write(parent_conn, b"pos\n")
                else:
                    print(f"No robot with id {robot_id}")

        elif command == "exit":
            shutdown_robots()
            break

        else:
            print("Invalid command")