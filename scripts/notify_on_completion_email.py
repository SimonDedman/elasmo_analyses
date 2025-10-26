#!/usr/bin/env python3
"""
Notification script with email support - alerts when download and pipeline complete.

Sends email to: simondedman@gmail.com
Also: desktop notification, sound, completion file
"""

import subprocess
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from datetime import datetime

EMAIL_TO = "simondedman@gmail.com"

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

def send_email(subject, body):
    """Send email using system mail command."""
    try:
        # Try using mail command (most reliable on Linux)
        process = subprocess.Popen(
            ['mail', '-s', subject, EMAIL_TO],
            stdin=subprocess.PIPE,
            text=True
        )
        process.communicate(input=body)

        if process.returncode == 0:
            return True
    except Exception as e:
        print(f"  ⚠️  Mail command failed: {e}")

    # Fallback: try sendmail
    try:
        msg = MIMEMultipart()
        msg['From'] = 'noreply@localhost'
        msg['To'] = EMAIL_TO
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        # Use local sendmail
        with subprocess.Popen(['/usr/sbin/sendmail', '-t', '-oi'],
                            stdin=subprocess.PIPE,
                            text=True) as proc:
            proc.communicate(msg.as_string())
            return proc.returncode == 0
    except Exception as e:
        print(f"  ⚠️  Sendmail failed: {e}")

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
        f.write("  ✅ Duplicate removal\n")
        f.write("  ✅ OCR processing\n")
        f.write("  ✅ Metadata extraction\n")
        f.write("\n")
        f.write("Ready for technique searching!\n")

    return completion_file

def get_statistics():
    """Gather final statistics."""
    try:
        # Count PDFs
        pdf_count_result = subprocess.run(
            ['find', '/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers',
             '-name', '*.pdf', '-type', 'f'],
            capture_output=True,
            text=True
        )
        pdf_count = len(pdf_count_result.stdout.strip().split('\n'))

        # Get download log stats
        log_file = Path("/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel/logs/scihub_download_log.csv")
        if log_file.exists():
            with open(log_file) as f:
                download_attempts = len(f.readlines()) - 1  # Exclude header

        # Get pipeline stats
        pipeline_state = Path("/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel/logs/pipeline_state.json")
        if pipeline_state.exists():
            import json
            with open(pipeline_state) as f:
                state = json.load(f)
                processed_count = len(state.get('processed', []))
        else:
            processed_count = 0

        return {
            'total_pdfs': pdf_count,
            'download_attempts': download_attempts if 'download_attempts' in locals() else 0,
            'processed_pdfs': processed_count
        }
    except Exception as e:
        print(f"  ⚠️  Could not gather statistics: {e}")
        return None

def main():
    """Monitor processes and notify on completion."""
    print("=" * 80)
    print("PROCESS COMPLETION MONITOR (with Email)")
    print("=" * 80)
    print("\nMonitoring:")
    print("  - Sci-Hub downloader")
    print("  - PDF pipeline processor")
    print(f"\nWill email: {EMAIL_TO}")
    print("Will also: desktop notification + sound + completion file")

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

            # Gather statistics
            stats = get_statistics()

            # Prepare email body
            email_subject = "🎉 PDF Processing Complete - EEA Data Panel"

            email_body = f"""Hi Simon,

Your PDF download and processing pipeline has completed!

COMPLETION TIME: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

PROCESSES COMPLETED:
  ✅ Sci-Hub PDF downloads
  ✅ Pipeline processing (deduplication, OCR, metadata)

"""

            if stats:
                email_body += f"""STATISTICS:
  • Total PDFs in collection: {stats['total_pdfs']:,}
  • Download attempts: {stats['download_attempts']:,}
  • PDFs processed through pipeline: {stats['processed_pdfs']:,}

"""

            email_body += """NEXT STEPS:
  1. Check results: /media/simon/data/Documents/Si Work/Papers & Books/SharkPapers/
  2. Review logs: /media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel/logs/
  3. Start technique searching when ready!

A completion file has been created at:
/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel/PROCESS_COMPLETE.txt

Best regards,
Your PDF Processing Pipeline
"""

            # Send notifications
            print("\n📢 Sending notifications...")

            # Email
            if send_email(email_subject, email_body):
                print(f"  ✅ Email sent to {EMAIL_TO}")
            else:
                print(f"  ⚠️  Email failed (check mail configuration)")

            # Desktop notification
            if send_desktop_notification(
                "PDF Processing Complete!",
                "Sci-Hub downloads and pipeline processing finished. Check your email!"
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
            print(f"\nEmail sent to: {EMAIL_TO}")
            break

if __name__ == "__main__":
    main()
