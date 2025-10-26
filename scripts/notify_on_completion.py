#!/usr/bin/env python3
"""
Notification script - alerts when download and pipeline complete.

Options:
1. Desktop notification (notify-send on Linux)
2. System beep/sound
3. Write completion flag file
4. Email (if configured)
"""

import subprocess
import time
from pathlib import Path
from datetime import datetime

def check_process_running(process_name):
    """Check if process is still running."""
    try:
        result = subprocess.run(
            ['pgrep', '-f', process_name],
            capture_output=True
        )
        return result.returncode == 0
    except:
        return False

def send_desktop_notification(title, message):
    """Send desktop notification (Linux)."""
    try:
        subprocess.run([
            'notify-send',
            '--urgency=critical',
            '--icon=dialog-information',
            title,
            message
        ])
        return True
    except:
        return False

def play_sound():
    """Play completion sound."""
    try:
        # Try different sound commands
        for cmd in [
            ['paplay', '/usr/share/sounds/freedesktop/stereo/complete.oga'],
            ['aplay', '/usr/share/sounds/alsa/Front_Center.wav'],
            ['beep']
        ]:
            try:
                subprocess.run(cmd, timeout=2)
                return True
            except:
                continue
    except:
        pass
    return False

def write_completion_file():
    """Write completion flag file."""
    completion_file = Path("/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel/PROCESS_COMPLETE.txt")

    with open(completion_file, 'w') as f:
        f.write(f"All processes completed at: {datetime.now().isoformat()}\n")
        f.write("\n")
        f.write("Completed:\n")
        f.write("  ✅ PDF downloads\n")
        f.write("  ✅ Pipeline processing\n")
        f.write("\n")
        f.write("Ready for technique searching!\n")

    return completion_file

def main():
    """Monitor processes and notify on completion."""
    print("=" * 80)
    print("PROCESS COMPLETION MONITOR")
    print("=" * 80)
    print("\nMonitoring:")
    print("  - Sci-Hub downloader")
    print("  - PDF pipeline processor")
    print("\nWill notify when both complete...")

    check_interval = 300  # Check every 5 minutes

    while True:
        downloader_running = check_process_running('scihub_downloader')
        pipeline_running = check_process_running('lightweight_pdf_pipeline')

        timestamp = datetime.now().strftime('%H:%M:%S')

        if downloader_running or pipeline_running:
            status = []
            if downloader_running:
                status.append("⏳ Downloader")
            if pipeline_running:
                status.append("⏳ Pipeline")

            print(f"[{timestamp}] Running: {', '.join(status)}")
            time.sleep(check_interval)
        else:
            # Both complete!
            print(f"\n[{timestamp}] ✅ ALL PROCESSES COMPLETE!")

            # Send notifications
            print("\n📢 Sending notifications...")

            # Desktop notification
            if send_desktop_notification(
                "PDF Processing Complete!",
                "Sci-Hub downloads and pipeline processing finished. Ready for technique analysis."
            ):
                print("  ✅ Desktop notification sent")

            # Sound
            if play_sound():
                print("  ✅ Sound played")

            # Completion file
            completion_file = write_completion_file()
            print(f"  ✅ Completion file: {completion_file}")

            print("\n" + "=" * 80)
            print("MONITORING COMPLETE")
            print("=" * 80)
            break

if __name__ == "__main__":
    main()
