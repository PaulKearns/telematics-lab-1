import argparse
import os
import sys
import signal
import time
from sensor import Sensor

# Global variables
robots = {}  # K = robot_id, V = PID
positions = {}  # K = robot_id, V = (row, col)
pipes = {}  # K = robot_id, V = (parent_to_child pipe, parent_from_child pipe)
treasures_found = set()
room_grid = None
num_treasures = None

# Signal handlers for master


def sigint_handler(sig, frame):
    print("\nReceived SIGINT. Shutting down")
    shutdown_robots()


def sigquit_handler(sig, frame):
    print("Replenishing batteries")
    # Send SIGUSR1 to each robot to signal battery replenishment
    for pid in robots.values():
        os.kill(pid, signal.SIGUSR1)


def sigtstp_handler(sig, frame):
    for robot_id, pid in robots.items():
        os.kill(pid, signal.SIGTSTP)  # Send SIGTSTP to each robot
        time.sleep(.1)
        _, parent_from_child_r = pipes[robot_id]
        response = os.read(parent_from_child_r, 1024).decode().strip()
        print(response)


def shutdown_robots():
    final_status = {}  # K = robot_id, V = final position and battery

    # Send 'exit' command to each robot to request last status and initiate shutdown
    for robot_id, (parent_to_child_w, child_to_parent_r) in pipes.items():
        os.write(parent_to_child_w, b"exit\n")

        # Read and store the final position and battery from each robot
        response = os.read(child_to_parent_r, 1024).decode().strip()
        final_status[robot_id] = response
        # Wait for each child process to exit
        _, status = os.waitpid(robots[robot_id], 0)
        print(f"Robot {robots[robot_id]} finished with status {status}")

    for robot_id, response in final_status.items():
        pid = robots[robot_id]
        print(f"Robot {robot_id} pid: {robots[robot_id]} last message:")
        print(response)
        print()

    print_room()
    sys.exit(0)


def start_robot(robot_id, position, battery, filename):
    # Create two pipes for bidirectional communication
    child_from_parent, parent_to_child = os.pipe()  # Parent-to-Child pipe
    parent_from_child, child_to_parent = os.pipe()  # Child-to-Parent pipe

    pid = os.fork()

    if pid == 0:  # Child process
        # Close unused ends of pipes
        os.close(parent_to_child)
        os.close(parent_from_child)

        # Redirect child's stdin to read end of pipe
        os.dup2(child_from_parent, sys.stdin.fileno())

        # Redirect child's stdout to write end of other pipe
        os.dup2(child_to_parent, sys.stdout.fileno())

        os.close(child_from_parent)
        os.close(child_to_parent)

        # Execute robot.py as the child process
        os.execvp("python3", ["python3", "robot.py", str(
            robot_id), "-f", filename, "-pos", str(position[0]), str(position[1]), "-b", str(battery)])
        sys.exit(0)

    else:  # Parent process
        # Close unused ends of pipes
        os.close(child_from_parent)
        os.close(child_to_parent)

        print(f'Robot {robot_id} PID: {pid} Position: {position}')

        # Store pipes, positions, and pids in dictionaries
        pipes[robot_id] = (parent_to_child, parent_from_child)
        positions[robot_id] = position
        robots[robot_id] = pid


# Function to send move command and handle responses for mv <robot_id/all> <direction>
def move_robot(robot_id, direction):
    new_position = calculate_new_position(positions[robot_id], direction)

    # Check for potential collisions first
    for other_robot_id, position in positions.items():
        if new_position == position and robot_id != other_robot_id:
            print(f"Collision between robot {robot_id} and {other_robot_id}")
            return

    # Write the move command to the child and wait for response
    child_from_parent, child_to_parent = pipes[robot_id]
    os.write(child_from_parent, f"mv {direction}\n".encode())
    response = os.read(child_to_parent, 1024).decode().strip()

    if "OK" in response:
        positions[robot_id] = new_position
        # Check if there is treasure in the new position
        os.write(child_from_parent, f"tr\n".encode())
        response = os.read(child_to_parent, 1024).decode().strip()
        if "Treasure" in response:
            treasures_found.add(positions[robot_id])
            # Treasure was not yet discovered
            if room_grid[positions[robot_id][0]][positions[robot_id][1]] != 'T':
                room_grid[positions[robot_id][0]][positions[robot_id][1]] = 'T'
                print(f"Treasure found by robot {robot_id}!")
                if len(treasures_found) == num_treasures:
                    print("All treasures found!")
                    shutdown_robots()
        else:
            room_grid[positions[robot_id][0]][positions[robot_id][1]] = '-'
        print(f"Robot {robot_id} status: OK")
    elif "KO" in response:
        print(f"Robot {robot_id} cannot move {direction}")
        print(f"Robot {robot_id} status: KO")
        if new_position[0] >= 0 and new_position[0] < room_dimensions[0] and new_position[1] >= 0 and new_position[1] < room_dimensions[1]:
            room_grid[new_position[0]][new_position[1]] = 'X'
    elif "stopped" in response:
        print(f"Robot {robot_id} is stopped")


def calculate_new_position(current_position, direction):
    if direction == "up":
        return (current_position[0] - 1, current_position[1])
    elif direction == "down":
        return (current_position[0] + 1, current_position[1])
    elif direction == "left":
        return (current_position[0], current_position[1] - 1)
    elif direction == "right":
        return (current_position[0], current_position[1] + 1)
    # TODO is there action to take if input here is invalid?


def print_room():
    grid_with_robots = [row[:] for row in room_grid]
    # Add 'R' in front of the current square if it is 'T'
    for robot_id, position in positions.items():
        row, col = position
        if room_grid[row][col] == 'T':
            grid_with_robots[row][col] = 'RT'
        else:  # Grid currently has '?' or '-'
            grid_with_robots[row][col] = 'R'
    print("Our information about the room so far:")
    for row in grid_with_robots:
        print(" ".join(row))
    print()


if __name__ == "__main__":
    # Use argparse to parse command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('-room', '--room_filename')
    parser.add_argument('-robots', '--robots_filename')
    args = parser.parse_args()

    ROOM_FILENAME = args.room_filename
    ROBOTS_FILENAME = args.robots_filename

    # Initialize Sensor and get relevant (allowed) information
    SENSOR = Sensor(ROOM_FILENAME)
    room_dimensions = SENSOR.dimensions()
    num_treasures = SENSOR.n_treasures()
    room_grid = [['?' for _ in range(room_dimensions[1])]
                 for _ in range(room_dimensions[0])]

    # Signal handling setup
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

    # Check if there is treasure at starting squares
    for robot_id, position in positions.items():
        child_from_parent, child_to_parent = pipes[robot_id]
        os.write(child_from_parent, f"tr\n".encode())
        response = os.read(child_to_parent, 1024).decode().strip()
        if "Treasure" in response:
            treasures_found.add(positions[robot_id])
            # Treasure was not yet discovered
            if room_grid[positions[robot_id][0]][positions[robot_id][1]] != 'T':
                room_grid[positions[robot_id][0]][positions[robot_id][1]] = 'T'
                if len(treasures_found) == num_treasures:
                    print("All treasures found!")
                    shutdown_robots()
        else:
            room_grid[positions[robot_id][0]][positions[robot_id][1]] = '-'
    print_room()

    # Begin CLI for user commands
    while True:
        action = input("Command: ").strip().split()
        command = action[0]

        if command == "mv":
            target, direction = action[1], action[2]
            if target == "all":
                for robot_id in sorted(robots):  # Move each robot sequentially
                    move_robot(robot_id, direction)
                print_room()
            else:
                robot_id = int(target)
                if robot_id in pipes:
                    move_robot(robot_id, direction)
                    print_room()
                else:
                    print(f"No robot with id {robot_id}")
        # Case: send bat command to target(s)
        elif command == "bat" and len(action) > 1:
            target = action[1]
            if target == "all":
                for robot_id, (parent_to_child_w, parent_from_child_r) in pipes.items():
                    os.write(parent_to_child_w, b"bat\n")
                    response = os.read(parent_from_child_r,
                                       1024).decode().strip()
                    print(f"Robot {robot_id} battery: {response}")
            else:
                robot_id = int(target)
                if robot_id in pipes:
                    parent_to_child_w, parent_from_child_r = pipes[robot_id]
                    os.write(parent_to_child_w, b"bat\n")
                    response = os.read(parent_from_child_r,
                                       1024).decode().strip()
                    print(f"Robot {robot_id} battery: {response}")
                else:
                    print(f"No robot with id {robot_id}")
        elif command == "pos":  # Case: send pos command to target(s)
            target = action[1]
            if target == "all":
                for robot_id, (parent_to_child_w, parent_from_child_r) in pipes.items():
                    os.write(parent_to_child_w, b"pos\n")
                    response = os.read(parent_from_child_r,
                                       1024).decode().strip()
                    print(f"Robot {robot_id} position: {response}")
            else:
                robot_id = int(target)
                if robot_id in pipes:
                    parent_to_child_w, parent_from_child_r = pipes[robot_id]
                    os.write(parent_to_child_w, b"pos\n")
                    response = os.read(parent_from_child_r,
                                       1024).decode().strip()
                    print(f"Robot {robot_id} position: {response}")
                else:
                    print(f"No robot with id {robot_id}")
        # Case: send SIGINT to target(s) to suspend
        elif command == "suspend":
            target = action[1]
            print(target)
            if target == "all":
                print("Suspending all robots")
                for pid in robots.values():
                    os.kill(pid, signal.SIGINT)
            else:
                robot_id = int(target)
                if robot_id in robots:
                    print(f"Suspending robot {robot_id}")
                    os.kill(robots[robot_id], signal.SIGINT)
                else:
                    print(f"No robot with id {robot_id}")
        # Case: send SIGQUIT to target(s) to resume
        elif command == "resume":
            target = action[1]
            if target == "all":
                print("Resuming all robots")
                for pid in robots.values():
                    os.kill(pid, signal.SIGQUIT)
            else:
                robot_id = int(target)
                if robot_id in robots:
                    print(f"Resuming robot {robot_id}")
                    os.kill(robots[robot_id], signal.SIGQUIT)
                else:
                    print(f"No robot with id {robot_id}")
        elif command == "exit":
            shutdown_robots()
            break
        else:
            print("Invalid command")
