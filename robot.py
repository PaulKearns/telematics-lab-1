import argparse
import os
import sys
import signal
from sensor import Sensor

FILENAME = None
SENSOR = None


class Robot:
    # Position = (row, col)
    def __init__(self, id, position=[0, 0], battery=100):
        self.id = id
        self.battery = battery
        self.is_suspended = False # Used to mark the robot as suspended
        if SENSOR.with_obstacle(position[0], position[1]):
            self.position = position
        else:
            print("Invalid initial position")
            exit()

    # Attempt to move the robot in the given direction
    def move(self, direction):
        if self.is_suspended:
            print(f"Robot {self.id} is stopped")
            return
        success = False
        if self.battery >= 5:
            if direction == "up":
                if SENSOR.with_obstacle(self.position[0] - 1, self.position[1]):
                    self.position[0] -= 1
                    success = True
            elif direction == "left":
                if SENSOR.with_obstacle(self.position[0], self.position[1] - 1):
                    self.position[1] -= 1
                    success = True
            elif direction == "right":
                if SENSOR.with_obstacle(self.position[0], self.position[1] + 1):
                    self.position[1] += 1
                    success = True
            else:
                if SENSOR.with_obstacle(self.position[0] + 1, self.position[1]):
                    self.position[0] += 1
                    success = True

        if success:
            print("OK")
            self.battery -= 5
        else:
            print(f"Robot 3 cannot move {direction}\nKO")

    def has_treasure(self):
        if self.is_suspended:
            print(f"Robot {self.id} is stopped")
            return
        if SENSOR.with_treasure(self.position[0], self.position[1]):
            print(f"Treasure at {self.position[0]} {self.position[1]}")
        else:
            print(f"Water at {self.position[0]} {self.position[1]}")

    def print_battery(self):
        if self.is_suspended:
            print(f"Robot {self.id} is stopped")
            return
        print(f'Battery: {robot.battery}')

    def print_position(self):
        if self.is_suspended:
            print(f"Robot {self.id} is stopped")
            return
        print(f'Position: {robot.position[0]} {robot.position[1]}')

    def shutdown(self):
        self.print_position()
        self.print_battery()
        exit(0)


if __name__ == "__main__":
    def sigint_handler(sig, frame):
        robot.is_suspended = True
        signal.signal(signal.SIGALRM, signal.SIG_IGN)

    def sigquit_handler(sig, frame):
        robot.is_suspended = False
        signal.signal(signal.SIGALRM, sigalrm_handler)
        signal.alarm(1)

    def sigtstp_handler(sig, frame):
        print(f"id: {robot.id} P: {robot.position} Bat: {robot.battery}", flush=True)

    def sigusr1_handler(sig, frame):
        robot.battery = 100

    def sigalrm_handler(sig, frame):
        if robot.battery > 0:
            robot.battery -= 1
        signal.alarm(1)

    signal.signal(signal.SIGINT, sigint_handler)
    signal.signal(signal.SIGQUIT, sigquit_handler)
    signal.signal(signal.SIGTSTP, sigtstp_handler)
    signal.signal(signal.SIGUSR1, sigusr1_handler)
    signal.signal(signal.SIGALRM, sigalrm_handler)
    signal.alarm(1)

    sys.stderr.write(f'PID: {os.getpid()}\n')

    # Initialize parser
    parser = argparse.ArgumentParser()

    # Adding optional argument
    parser.add_argument('robot_id')
    parser.add_argument('-f', '--filename')
    parser.add_argument('-pos', '--position', nargs=2,
                        type=int, default=[0, 0])
    parser.add_argument('-b', '--battery', type=int, default=100)

    # Read arguments from command line
    args = parser.parse_args()
    FILENAME = args.filename
    SENSOR = Sensor(FILENAME)
    robot = Robot(args.robot_id, args.position, args.battery)

    # Begin CLI
    '''
    print("""\n\nWhat would you like to do next?
                            mv <direction>: tries to move the robot one cell in the specified direction. (up, down, left, right). If it is possible, the robots changes its position and prints OK. If it is not possible to move in the specified direction, its position does not change and prints KO.
                            bat: prints the current battery level.
                            pos: prints the current position of the robot as a 2-dimension vector.
                            tr: checks if there is a treasure in the current position. If there is a treasure, it prints Treasure. If not, prints Water.
                            exit: the program prints the current position of the robot and its battery level and exits.\n""")
    '''
    while True:
        action = input("")
        action = action.split(' ')
        if len(action) > 1:
            direction = action[1]
        action = action[0]
        match action:
            case 'mv':
                robot.move(direction)
            case 'bat':
                robot.print_battery()
            case 'pos':
                robot.print_position()
            case 'tr':
                robot.has_treasure()
            case 'exit':
                robot.shutdown()
                break
            case _:
                print("Invalid command")
