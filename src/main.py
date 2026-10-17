import platform
import sys

def main():
    print("IBM Z Datathon Environment Check")
    print("-------------------------------")
    print(f"Python version: {sys.version.split()[0]}")
    print(f"Architecture: {platform.machine()}")
    print("Project environment is working!")

if __name__ == "__main__":
    main()
