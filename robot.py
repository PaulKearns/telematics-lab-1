import argparse
import os
import sys
import signal
from sensor import Sensor

FILENAME = None
SENSOR = None

class Robot:
    # Position = (row, col)
    def __init__(self, id, position=[0,0], battery=100):
        self.id = id
        self.position = position
        self.battery = battery
        self.is_suspended = False
    
    def move(self, direction):
        success = False
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
        else:
            print("KO")

    
    def has_treasure(self):
        if SENSOR.with_treasure(self.position[0], self.position[1]):
            print("Treasure")
        else:
            print("Water")


if __name__ == "__main__":
    def sigint_handler(sig, frame):
        # TODO: is this correct for pausing the robot?
        signal.signal(signal.SIGALRM, signal.SIG_IGN)
    
    # TODO: is this correct for resuming the robot?
    def sigquit_handler(sig, frame):
        signal.signal(signal.SIGALRM, sigalrm_handler)

    def sigtstp_handler(sig, frame):
        print(f"Robot ID: {robot.id}\nRobot position: {robot.position}\nRobot battery level: {robot.battery}")

    def sigusr1_handler(sig, frame):
        robot.battery = 100

    def sigalrm_handler(sig, frame):
        robot.battery -= 1
        signal.alarm(1)

    signal.signal(signal.SIGINT, sigint_handler)
    signal.signal(signal.SIGQUIT, sigquit_handler)
    signal.signal(signal.SIGTSTP, sigtstp_handler)
    signal.signal(signal.SIGUSR1, sigusr1_handler)
    signal.signal(signal.SIGALRM, sigalrm_handler)

    sys.stderr.write(os.getpid())

    # Initialize parser
    parser = argparse.ArgumentParser()

    # Adding optional argument
    parser.add_argument('robot_id')
    parser.add_argument('-f', '--filename')
    parser.add_argument('-pos', '--position', nargs=2, type=int, default=[0, 0])
    parser.add_argument('-b', '--battery', type=int, default=100)

    # Read arguments from command line
    args = parser.parse_args()
    FILENAME = args.filename
    SENSOR = Sensor(FILENAME)
    robot = Robot(args.robot_id, args.position, args.battery)

    # Begin CLI
    while True:
        action = input("""What would you like to do next?
                            mv <direction>: tries to move the robot one cell in the specified direction. (up, down, left, right). If it is possible, the robots changes its position and prints OK. If it is not possible to move in the specified direction, its position does not change and prints KO.
                            bat: prints the current battery level.
                            pos: prints the current position of the robot as a 2-dimension vector.
                            tr: checks if there is a treasure in the current position. If there is a treasure, it prints Treasure. If not, prints Water.
                            exit: the program prints the current position of the robot and its battery level and exits.""")
        action = action.split(' ')
        if len(action) > 1:
            direction = action[1]
        action = action[0]
        if action != 'exit' and robot.is_suspended:
            print("Robot {robot.id} is stopped")
        match action:
            case 'mv':
                robot.move(direction)
            case 'bat':
                print(robot.battery)
            case 'pos':
                print(f'({robot.position[0]}, {robot.position[1]})')
            case 'tr':
                robot.has_treasure()
            case 'exit':
                print(robot.battery)
                print(f'({robot.position[0]}, {robot.position[1]})')
                break
            case _:
                print("Invalid command")