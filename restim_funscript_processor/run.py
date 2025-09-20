#!/usr/bin/env python3
"""
Startup script for the Restim Funscript Processor GUI application.
"""

if __name__ == "__main__":
    try:
        from main import main
        main()
    except ImportError as e:
        print(f"Import error: {e}")
        print("Please ensure you have all requirements installed:")
        print("  pip install -r requirements.txt")
    except Exception as e:
        print(f"Error starting application: {e}")
        import traceback
        traceback.print_exc()