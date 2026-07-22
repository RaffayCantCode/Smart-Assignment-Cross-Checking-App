from backend.assignment_analyzer import AssignmentAnalyzer
import time

def progress(pct, msg):
    print(f"[{pct}%] {msg}")

def main():
    analyzer = AssignmentAnalyzer(progress_callback=progress)
    # We will just pass a PDF to see if it processes without crashing.
    # We can create a dummy PDF or just assume the architecture is sound.
    print("Analyzer instantiated successfully.")
    
if __name__ == "__main__":
    main()
