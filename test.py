# Test the Sensor class
# This program uses the Sensor class to read the room information from a file and print the room.
# The program reads the filename from the command line and creates an instance of the Sensor class with the filename.
# The program calls the read_room() method to read the room information from the file.
# The program calls the print_room() method to print the room.
# The program should be executed from the command line as follows:
# python test.py room.txt

import sys
import sensor

def main():
    if len(sys.argv) != 2:
        print(f'Usage: python {sys.argv[0]} filename')
        sys.exit(1)
    filename = sys.argv[1]
    s = sensor.Sensor(filename)

    # this method cannot be invoked by the master or the robot
    # it is only "for us"
    s.print_room()
    
    #methods that can be used only by the master
    print(f'dimensions of the room: {s.dimensions()}')
    print(f'number of treasures: {s.n_treasures()}')

    # checking a position: this methods are only meant for the robots
    # the master can use them only at the beginning to check if the
    # initial position of a robot contains an obstacle or a treasure
    my_row=2
    my_col=3
    
    if (s.with_obstacle(my_row,my_col)):
        print (f'({my_row},{my_col}) has no obstacle')
    else:
        print (f'({my_row},{my_col}) has an obstacle')

    if (s.with_treasure(my_row,my_col)):
        print (f'({my_row},{my_col}) has a treasure')
    else:
        print (f'({my_row},{my_col}) has no treasure')

if __name__ == '__main__':
    main()
