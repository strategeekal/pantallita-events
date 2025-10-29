#!/usr/bin/env python3
"""
SCREENY Management Tool
Unified manager for events and schedules on your display screens
Automatically detects available images from local folders
"""
import csv
import re
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

# ============================================================================
# CONFIGURATION - UPDATE THESE PATHS TO MATCH YOUR SETUP
# ============================================================================

# Path to your local SCREENY project folders
PROJECT_ROOT = Path.home() / "Documents" / "Adafruit" / "SCREENY V2.0"
EVENTS_IMAGES_FOLDER = PROJECT_ROOT / "img" / "events"
SCHEDULES_IMAGES_FOLDER = PROJECT_ROOT / "img" / "schedules"

# CSV files
EVENTS_CSV = "ephemeral_events.csv"
SCHEDULES_FOLDER = Path("schedules")

# Valid colors for events and schedules
VALID_COLORS = [
	"MINT", "BUGAMBILIA", "LILAC", "RED", "GREEN", "BLUE",
	"ORANGE", "YELLOW", "CYAN", "PURPLE", "PINK", "AQUA", "WHITE",
	"BROWN", "BEIGE", "DARK_GRAY", "GRAY", "DIMMEST_WHITE"
]

# Valid days (0=Monday, 6=Sunday) - CHANGE THIS IF NEEDED
VALID_DAYS = "0123456"
DAY_NAMES = {
	"0": "Mon", "1": "Tue", "2": "Wed", "3": "Thu",
	"4": "Fri", "5": "Sat", "6": "Sun"
}

# ============================================================================
# SHARED UTILITIES
# ============================================================================

def get_available_images(image_type="events"):
	"""Scan local images folder for .bmp files"""
	folder = EVENTS_IMAGES_FOLDER if image_type == "events" else SCHEDULES_IMAGES_FOLDER
	
	if not folder.exists():
		print(f"⚠️  Warning: Images folder not found: {folder}")
		return []
	
	bmp_files = sorted([f.name for f in folder.glob("*.bmp")])
	return bmp_files


def validate_image(image_name, image_type="events"):
	"""Validate image file name against available images"""
	available_images = get_available_images(image_type)
	
	if not available_images:
		if not image_name.endswith('.bmp'):
			return False, "Image must be a .bmp file"
		return True, "OK (couldn't verify against local folder)"
	
	if image_name not in available_images:
		folder = EVENTS_IMAGES_FOLDER if image_type == "events" else SCHEDULES_IMAGES_FOLDER
		return False, f"Image '{image_name}' not found in {folder}"
	
	return True, "OK"


def validate_color(color):
	"""Validate color name"""
	color_upper = color.upper()
	if color_upper not in VALID_COLORS:
		return False, f"Color must be one of: {', '.join(VALID_COLORS[:10])}..."
	return True, "OK"


def git_pull():
	"""Pull latest changes from GitHub"""
	try:
		print("\n📥 Pulling latest from GitHub...")
		
		# Configure pull strategy if needed
		config_check = subprocess.run(
			['git', 'config', 'pull.rebase'],
			capture_output=True,
			text=True
		)
		
		if config_check.returncode != 0:
			subprocess.run(
				['git', 'config', 'pull.rebase', 'false'],
				capture_output=True
			)
		
		# Pull with merge strategy
		result = subprocess.run(
			['git', 'pull', '--no-rebase'],
			capture_output=True,
			text=True,
			cwd='.'
		)
		
		if result.returncode == 0:
			print("✓ Successfully pulled from GitHub!")
			if "Already up to date" in result.stdout:
				print("  (No changes - already up to date)")
			else:
				print(f"  {result.stdout.strip()}")
			return True
		else:
			if "CONFLICT" in result.stdout or "CONFLICT" in result.stderr:
				print("❌ Merge conflict detected! Resolve manually.")
			else:
				print(f"❌ Pull failed: {result.stderr}")
			return False
			
	except Exception as e:
		print(f"❌ Git error: {e}")
		return False


def git_push(commit_message=None):
	"""Push changes to GitHub"""
	try:
		# Check if git is available
		result = subprocess.run(['git', 'status'], capture_output=True, text=True)
		if result.returncode != 0:
			print("❌ Not a git repository or git not installed")
			return False
		
		# Check what's changed
		status_result = subprocess.run(['git', 'status', '--short'], capture_output=True, text=True)
		if not status_result.stdout.strip():
			print("ℹ️  No changes to push")
			return True
		
		print(f"\n📝 Changes to push:")
		print(status_result.stdout)
		
		# Add all changes
		subprocess.run(['git', 'add', '.'], check=True)
		
		# Commit
		if not commit_message:
			commit_message = f"Update SCREENY data - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
		
		subprocess.run(['git', 'commit', '-m', commit_message], check=True)
		
		# Push
		print("\n📤 Pushing to GitHub...")
		result = subprocess.run(['git', 'push'], capture_output=True, text=True)
		
		if result.returncode == 0:
			print("✓ Successfully pushed to GitHub!")
			print("\n💡 Your SCREENY devices will fetch updates:")
			print("   - Automatically at 3 AM daily restart")
			print("   - Or restart them manually now")
			return True
		else:
			print(f"❌ Push failed: {result.stderr}")
			return False
			
	except subprocess.CalledProcessError as e:
		print(f"❌ Git error: {e}")
		return False
	except FileNotFoundError:
		print("❌ Git not found. Install git or push manually")
		return False


# ============================================================================
# EVENT MANAGEMENT (from your existing code)
# ============================================================================

class EventValidator:
	"""Validates event data"""
	
	@staticmethod
	def validate_date(date_str):
		"""Validate date format YYYY-MM-DD and ensure it's not in the past"""
		if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
			return False, "Date must be in YYYY-MM-DD format"
		
		try:
			event_date = datetime.strptime(date_str, '%Y-%m-%d')
			today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
			
			if event_date < today:
				return False, f"Date is in the past (today is {today.strftime('%Y-%m-%d')})"
			
			return True, "OK"
		except ValueError:
			return False, "Invalid date"
	
	@staticmethod
	def validate_text(text, field_name, max_length=12):
		"""Validate text fields"""
		if not text or not text.strip():
			return False, f"{field_name} cannot be empty"
		
		if len(text) > max_length:
			return False, f"{field_name} too long (max {max_length} chars)"
		
		return True, "OK"
	
	@staticmethod
	def validate_time(hour_str, field_name):
		"""Validate hour (0-23)"""
		try:
			hour = int(hour_str)
			if 0 <= hour <= 23:
				return True, "OK"
			else:
				return False, f"{field_name} must be 0-23"
		except ValueError:
			return False, f"{field_name} must be a number"
	
	@classmethod
	def validate_event(cls, date, top_line, bottom_line, image, color, start_hour=None, end_hour=None):
		"""Validate complete event"""
		errors = []
		
		valid, msg = cls.validate_date(date)
		if not valid:
			errors.append(f"Date: {msg}")
		
		valid, msg = cls.validate_text(top_line, "Top Line", max_length=12)
		if not valid:
			errors.append(msg)
		
		valid, msg = cls.validate_text(bottom_line, "Bottom Line", max_length=12)
		if not valid:
			errors.append(msg)
		
		valid, msg = validate_image(image, "events")
		if not valid:
			errors.append(msg)
		
		valid, msg = validate_color(color)
		if not valid:
			errors.append(msg)
		
		if start_hour is not None:
			valid, msg = cls.validate_time(start_hour, "Start hour")
			if not valid:
				errors.append(msg)
		
		if end_hour is not None:
			valid, msg = cls.validate_time(end_hour, "End hour")
			if not valid:
				errors.append(msg)
		
		if start_hour is not None and end_hour is not None:
			try:
				if int(start_hour) >= int(end_hour):
					errors.append("Start hour must be before end hour")
			except ValueError:
				pass
		
		return len(errors) == 0, errors


class EventManager:
	"""Manages ephemeral events"""
	
	def __init__(self, filename=EVENTS_CSV):
		self.filename = filename
		self.events = []
		self.load_events()
	
	def load_events(self):
		"""Load existing events from CSV"""
		if not Path(self.filename).exists():
			print(f"📝 Creating new file: {self.filename}")
			return
		
		with open(self.filename, 'r') as f:
			reader = csv.reader(f)
			for row in reader:
				if row and not row[0].startswith('#'):
					self.events.append(row)
		
		print(f"✓ Loaded {len(self.events)} events from {self.filename}")
	
	def add_event(self, date, top_line, bottom_line, image, color="MINT", start_hour=None, end_hour=None):
		"""Add a new event with validation"""
		valid, errors = EventValidator.validate_event(date, top_line, bottom_line, image, color, start_hour, end_hour)
		
		if not valid:
			print("❌ Validation failed:")
			for error in errors:
				print(f"   - {error}")
			return False
		
		event = [date, top_line, bottom_line, image, color.upper()]
		
		if start_hour is not None and end_hour is not None:
			event.append(str(start_hour))
			event.append(str(end_hour))
		
		self.events.append(event)
		
		time_info = f" ({start_hour}:00-{end_hour}:00)" if start_hour is not None else " (all day)"
		print(f"✓ Added: {date} - {top_line} / {bottom_line}{time_info}")
		return True
	
	def list_events(self):
		"""List all events with past/future separation"""
		if not self.events:
			print("No events found.")
			return
		
		today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
		past_events = []
		future_events = []
		
		for i, event in enumerate(self.events):
			try:
				event_date = datetime.strptime(event[0], '%Y-%m-%d')
				if event_date < today:
					past_events.append((i, event))
				else:
					future_events.append((i, event))
			except:
				future_events.append((i, event))
		
		print("\n📅 Current Events:")
		print("=" * 90)
		
		if future_events:
			print(f"\n🔮 FUTURE EVENTS ({len(future_events)} will be imported):")
			print("-" * 90)
			for i, event in future_events:
				self._print_event(i, event)
		
		if past_events:
			print(f"\n📜 PAST EVENTS ({len(past_events)} will be skipped):")
			print("-" * 90)
			for i, event in past_events:
				self._print_event(i, event)
		
		print("=" * 90)
		print(f"Total: {len(self.events)} events ({len(future_events)} future, {len(past_events)} past)\n")
	
	def _print_event(self, i, event):
		"""Helper to print a single event"""
		date = event[0]
		top_line = event[1]
		bottom_line = event[2]
		image = event[3]
		color = event[4] if len(event) > 4 else "MINT"
		
		if len(event) >= 7:
			time_str = f" [{event[5]}:00-{event[6]}:00]"
		else:
			time_str = " [all day]"
		
		print(f"{i:2d}. {date} | {top_line:12s} / {bottom_line:12s} | {image:20s} | {color:10s}{time_str}")
	
	def save(self):
		"""Save events to CSV"""
		self.events.sort(key=lambda x: x[0])
		
		with open(self.filename, 'w', newline='') as f:
			f.write('# Ephemeral Events - Auto-generated\n')
			f.write('# Format: YYYY-MM-DD,TopLine,BottomLine,Image,Color[,StartHour,EndHour]\n')
			f.write('# TopLine = displays on TOP of screen\n')
			f.write('# BottomLine = displays on BOTTOM (usually the name)\n')
			f.write('# Times are optional (24-hour format, 0-23). If omitted, event shows all day.\n')
			
			writer = csv.writer(f)
			for event in self.events:
				writer.writerow(event)
		
		print(f"✓ Saved {len(self.events)} events to {self.filename}")


# ============================================================================
# SCHEDULE MANAGEMENT (NEW)
# ============================================================================

class ScheduleValidator:
	"""Validates schedule data"""
	
	@staticmethod
	def validate_schedule_date(date_str):
		"""Validate schedule date (can be future, present, or past)"""
		if date_str.lower() == "default":
			return True, "OK"
		
		if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
			return False, "Date must be in YYYY-MM-DD format or 'default'"
		
		try:
			datetime.strptime(date_str, '%Y-%m-%d')
			return True, "OK"
		except ValueError:
			return False, "Invalid date"
	
	@staticmethod
	def validate_schedule_name(name):
		"""Validate schedule name"""
		if not name or not name.strip():
			return False, "Schedule name cannot be empty"
		
		if len(name) > 30:
			return False, "Schedule name too long (max 30 chars)"
		
		return True, "OK"
	
	@staticmethod
	def validate_days(days_str):
		"""Validate days string (e.g., '12345' for Mon-Fri)"""
		if not days_str or not days_str.strip():
			return False, "Days cannot be empty"
		
		# Check all characters are 1-7
		for char in days_str:
			if char not in VALID_DAYS:
				return False, f"Days must contain only 1-7 (found '{char}')"
		
		# Check for duplicates
		if len(set(days_str)) != len(days_str):
			return False, "Days contains duplicates"
		
		return True, "OK"
	
	@staticmethod
	def validate_time_format(time_str):
		"""Validate HH:MM format"""
		if not re.match(r'^\d{1,2}:\d{2}$', time_str):
			return False, "Time must be in HH:MM format"
		
		try:
			hour, minute = map(int, time_str.split(':'))
			if not (0 <= hour <= 23 and 0 <= minute <= 59):
				return False, "Hour must be 0-23, minute must be 0-59"
			return True, "OK"
		except ValueError:
			return False, "Invalid time"
	
	@staticmethod
	def validate_time_range(start_time, end_time):
		"""Validate start time is before end time"""
		try:
			start_h, start_m = map(int, start_time.split(':'))
			end_h, end_m = map(int, end_time.split(':'))
			
			start_mins = start_h * 60 + start_m
			end_mins = end_h * 60 + end_m
			
			if start_mins >= end_mins:
				return False, "Start time must be before end time"
			
			return True, "OK"
		except:
			return False, "Invalid time format"
	
	@classmethod
	def validate_schedule(cls, name, days, start_time, end_time, image):
		"""Validate complete schedule"""
		errors = []
		
		valid, msg = cls.validate_schedule_name(name)
		if not valid:
			errors.append(msg)
		
		valid, msg = cls.validate_days(days)
		if not valid:
			errors.append(msg)
		
		valid, msg = cls.validate_time_format(start_time)
		if not valid:
			errors.append(f"Start time: {msg}")
		
		valid, msg = cls.validate_time_format(end_time)
		if not valid:
			errors.append(f"End time: {msg}")
		
		if not errors:  # Only check range if both times are valid
			valid, msg = cls.validate_time_range(start_time, end_time)
			if not valid:
				errors.append(msg)
		
		valid, msg = validate_image(image, "schedules")
		if not valid:
			errors.append(msg)
		
		return len(errors) == 0, errors


class ScheduleManager:
	"""Manages date-specific and default schedules"""
	
	def __init__(self):
		self.schedules = {}  # Key: date (YYYY-MM-DD or 'default'), Value: list of schedule entries
		self.load_all_schedules()
	
	def load_all_schedules(self):
		"""Load all schedule files from schedules folder"""
		if not SCHEDULES_FOLDER.exists():
			print(f"📝 Creating schedules folder: {SCHEDULES_FOLDER}")
			SCHEDULES_FOLDER.mkdir(exist_ok=True)
			return
		
		csv_files = list(SCHEDULES_FOLDER.glob("*.csv"))
		
		if not csv_files:
			print("📝 No schedule files found")
			return
		
		for csv_file in csv_files:
			date_key = csv_file.stem  # e.g., '2025-10-31' or 'default'
			self.schedules[date_key] = self._load_schedule_file(csv_file)
		
		print(f"✓ Loaded schedules for {len(self.schedules)} dates")
	
	def _load_schedule_file(self, filepath):
		"""Load a single schedule CSV file (skips comments, no header row expected)"""
		schedules = []
		
		try:
			with open(filepath, 'r') as f:
				for line_num, line in enumerate(f, 1):
					line = line.strip()
					
					# Skip empty lines and comments
					if not line or line.startswith('#'):
						continue
					
					# Parse CSV data directly
					parts = [p.strip() for p in line.split(',')]
					
					# Need at least 9 fields
					if len(parts) < 9:
						print(f"⚠️  Line {line_num} in {filepath.name}: expected 9 fields, got {len(parts)}")
						continue
					
					schedule = {
						'name': parts[0],
						'enabled': parts[1],
						'days': parts[2],
						'start_hour': parts[3],
						'start_min': parts[4],
						'end_hour': parts[5],
						'end_min': parts[6],
						'image': parts[7],
						'progressbar': parts[8]
					}
					
					schedules.append(schedule)
				
				if schedules:
					print(f"✓ Loaded {len(schedules)} schedule(s) from {filepath.name}")
					
		except Exception as e:
			print(f"⚠️  Error loading {filepath.name}: {e}")
		
		return schedules
	
	def list_schedules(self):
		"""List all schedules organized by date"""
		if not self.schedules:
			print("No schedules found.")
			return
		
		print("\n📅 Current Schedules:")
		print("=" * 100)
		
		# Separate default and date-specific
		default_schedules = self.schedules.get('default', [])
		date_schedules = {k: v for k, v in self.schedules.items() if k != 'default'}
		
		# Show default first
		if default_schedules:
			print(f"\n📌 DEFAULT SCHEDULE ({len(default_schedules)} items):")
			print("-" * 100)
			for schedule in default_schedules:
				self._print_schedule(schedule)
		
		# Show date-specific schedules by month
		if date_schedules:
			# Group by month
			by_month = defaultdict(list)
			for date_str, schedule_list in sorted(date_schedules.items()):
				try:
					date_obj = datetime.strptime(date_str, '%Y-%m-%d')
					month_key = date_obj.strftime('%Y-%m')
					by_month[month_key].append((date_str, date_obj, schedule_list))
				except:
					pass
			
			# Print by month
			today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
			
			for month_key in sorted(by_month.keys()):
				month_name = datetime.strptime(month_key, '%Y-%m').strftime('%B %Y')
				print(f"\n📆 {month_name.upper()}:")
				print("-" * 100)
				
				for date_str, date_obj, schedule_list in sorted(by_month[month_key], key=lambda x: x[1]):
					day_name = date_obj.strftime('%a')
					
					# Mark today
					today_marker = " ← TODAY" if date_obj == today else ""
					past_marker = " (past)" if date_obj < today else ""
					
					print(f"\n  📅 {date_str} ({day_name}){today_marker}{past_marker} - {len(schedule_list)} schedule(s):")
					for schedule in schedule_list:
						print("     ", end="")
						self._print_schedule(schedule)
		
		print("=" * 100)
		print(f"Total: {sum(len(v) for v in self.schedules.values())} schedules across {len(self.schedules)} dates\n")
	
	def _print_schedule(self, schedule):
		"""Helper to print a single schedule entry"""
		name = schedule.get('name', 'Unnamed')
		enabled = "✓" if schedule.get('enabled') == '1' else "✗"
		days = schedule.get('days', '')
		
		# Safe formatting with defaults
		start_h = schedule.get('start_hour', '0')
		start_m = schedule.get('start_min', '0')
		end_h = schedule.get('end_hour', '0')
		end_m = schedule.get('end_min', '0')
		
		# Ensure strings for zfill
		start = f"{str(start_h)}:{str(start_m).zfill(2)}"
		end = f"{str(end_h)}:{str(end_m).zfill(2)}"
		
		image = schedule.get('image', '')
		progress = "📊" if schedule.get('progressbar') == '1' else "  "
		
		# Convert days to day names safely
		day_names = [DAY_NAMES[d] for d in str(days) if d in DAY_NAMES]
		days_str = ','.join(day_names) if day_names else 'None'
		
		print(f"{enabled} {name:25s} | {days_str:20s} | {start}-{end} | {image:20s} {progress}")
	
	def add_schedule(self, date, name, days, start_time, end_time, image, progressbar=True):
		"""Add a new schedule to a specific date"""
		# Validate
		valid, errors = ScheduleValidator.validate_schedule(name, days, start_time, end_time, image)
		
		if not valid:
			print("❌ Validation failed:")
			for error in errors:
				print(f"   - {error}")
			return False
		
		# Parse times
		start_h, start_m = map(int, start_time.split(':'))
		end_h, end_m = map(int, end_time.split(':'))
		
		# Create schedule entry
		schedule = {
			'name': name,
			'enabled': '1',
			'days': days,
			'start_hour': str(start_h),
			'start_min': str(start_m),
			'end_hour': str(end_h),
			'end_min': str(end_m),
			'image': image,
			'progressbar': '1' if progressbar else '0'
		}
		
		# Add to schedules
		if date not in self.schedules:
			self.schedules[date] = []
		
		self.schedules[date].append(schedule)
		
		print(f"✓ Added schedule to {date}: {name} ({start_time}-{end_time})")
		return True
	
	def save_all(self):
		"""Save all schedules to their respective files"""
		if not self.schedules:
			print("No schedules to save.")
			return
		
		SCHEDULES_FOLDER.mkdir(exist_ok=True)
		
		for date_key, schedule_list in self.schedules.items():
			if not schedule_list:
				continue
			
			filepath = SCHEDULES_FOLDER / f"{date_key}.csv"
			
			with open(filepath, 'w', newline='') as f:
				# Write comment header (for human readability)
				f.write('# Format: name,enabled,days,start_hour,start_min,end_hour,end_min,image,progressbar\n')
				f.write('# enabled: 1=true, 0=false\n')
				f.write('# days: 0-6 for Mon-Sun (e.g., "01234" = Mon-Fri)\n')
				f.write('# progressbar: 1=true, 0=false\n')
				
				# Write data directly (no CSV header row)
				writer = csv.writer(f)
				for schedule in schedule_list:
					row = [
						schedule['name'],
						schedule['enabled'],
						schedule['days'],
						schedule['start_hour'],
						schedule['start_min'],
						schedule['end_hour'],
						schedule['end_min'],
						schedule['image'],
						schedule['progressbar']
					]
					writer.writerow(row)
			
			print(f"✓ Saved {len(schedule_list)} schedule(s) to {filepath.name}")
		
		print(f"\n✓ Saved all schedules ({len(self.schedules)} files)")
	
	def delete_schedule_file(self, date):
		"""Delete entire schedule file for a date"""
		if date not in self.schedules:
			print(f"❌ No schedule found for {date}")
			return False
		
		filepath = SCHEDULES_FOLDER / f"{date}.csv"
		
		try:
			if filepath.exists():
				filepath.unlink()
			
			del self.schedules[date]
			print(f"✓ Deleted schedule file: {date}.csv")
			return True
		except Exception as e:
			print(f"❌ Error deleting {date}.csv: {e}")
			return False
	
	def cleanup_past_schedules(self, days_threshold=30):
		"""Remove schedule files older than threshold"""
		today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
		cutoff_date = today - timedelta(days=days_threshold)
		
		to_delete = []
		
		for date_key in self.schedules.keys():
			if date_key == 'default':
				continue
			
			try:
				date_obj = datetime.strptime(date_key, '%Y-%m-%d')
				if date_obj < cutoff_date:
					to_delete.append((date_key, date_obj))
			except:
				pass
		
		if not to_delete:
			print(f"✓ No schedules older than {days_threshold} days")
			return
		
		print(f"\n🗑️  Found {len(to_delete)} schedule(s) older than {days_threshold} days:")
		for date_key, date_obj in sorted(to_delete, key=lambda x: x[1]):
			days_ago = (today - date_obj).days
			print(f"  - {date_key} ({days_ago} days ago)")
		
		confirm = input(f"\nDelete these {len(to_delete)} old schedules? (y/n): ").strip().lower()
		
		if confirm == 'y':
			for date_key, _ in to_delete:
				self.delete_schedule_file(date_key)
			print(f"\n✓ Cleaned up {len(to_delete)} old schedules")
		else:
			print("Cancelled")


# ============================================================================
# MAIN MENU
# ============================================================================

def main_menu():
	"""Main menu for choosing between events and schedules"""
	
	# Auto-pull on startup
	print("\n📥 Checking for updates from GitHub...")
	try:
		git_pull()
	except:
		print("⚠️  Could not pull from GitHub (using local version)")
	
	event_manager = None
	schedule_manager = None
	
	while True:
		print("\n" + "="*80)
		print("🎨 SCREENY MANAGEMENT TOOL")
		print("="*80)
		print("1. Manage Events")
		print("2. Manage Schedules")
		print("3. Push ALL to GitHub (events + schedules)")
		print("4. Pull latest from GitHub")
		print("0. Exit")
		print()
		
		choice = input("Choose an option (0-4): ").strip()
		
		if choice == "1":
			# Initialize event manager if needed
			if event_manager is None:
				event_manager = EventManager()
			event_menu(event_manager)
		
		elif choice == "2":
			# Initialize schedule manager if needed
			if schedule_manager is None:
				schedule_manager = ScheduleManager()
			schedule_menu(schedule_manager)
		
		elif choice == "3":
			# Push everything
			print("\n📦 Preparing to push all changes to GitHub...")
			
			# Save everything first
			if event_manager:
				event_manager.save()
			if schedule_manager:
				schedule_manager.save_all()
			
			# Review what will be pushed
			print("\n📋 Review changes:")
			if event_manager and event_manager.events:
				print(f"  ✓ {len(event_manager.events)} events")
			if schedule_manager and schedule_manager.schedules:
				total_schedules = sum(len(v) for v in schedule_manager.schedules.values())
				print(f"  ✓ {total_schedules} schedules across {len(schedule_manager.schedules)} dates")
			
			confirm = input("\nPush to GitHub? (y/n): ").strip().lower()
			if confirm == 'y':
				if git_push():
					print("\n✅ All changes pushed to GitHub!")
			else:
				print("Push cancelled")
		
		elif choice == "4":
			git_pull()
			# Reload managers
			event_manager = None
			schedule_manager = None
			print("\n✓ Reloaded data from disk")
		
		elif choice == "0":
			confirm = input("Exit? (y/n): ").strip().lower()
			if confirm == 'y':
				print("Goodbye!")
				break
		
		else:
			print("❌ Invalid choice")


def event_menu(manager):
	"""Event management submenu"""
	while True:
		print("\n" + "="*80)
		print("📅 EVENT MANAGEMENT")
		print("="*80)
		print("1. List all events")
		print("2. Add new event")
		print("3. Edit event")
		print("4. Remove event")
		print("5. Show available images")
		print("6. Validate all events")
		print("7. Clean up past events")
		print("8. Save changes (local only)")
		print("0. Back to main menu")
		print()
		
		choice = input("Choose option (0-8): ").strip()
		
		if choice == "1":
			manager.list_events()
		
		elif choice == "2":
			add_event_interactive(manager)
		
		elif choice == "3":
			manager.list_events()
			if not manager.events:
				print("❌ No events to edit")
				continue
			
			try:
				index = int(input("\nEnter event number to edit: "))
				if 0 <= index < len(manager.events):
					edit_event_interactive(manager, index)
				else:
					print("❌ Invalid event number")
			except ValueError:
				print("❌ Invalid number")
		
		elif choice == "4":
			manager.list_events()
			if not manager.events:
				continue
			
			try:
				index = int(input("\nEnter event number to remove: "))
				if 0 <= index < len(manager.events):
					event = manager.events[index]
					confirm = input(f"Delete event '{event[1]} / {event[2]}' on {event[0]}? (y/n): ").strip().lower()
					if confirm == 'y':
						manager.events.pop(index)
						print("✓ Event removed")
				else:
					print("❌ Invalid event number")
			except ValueError:
				print("❌ Invalid number")
		
		elif choice == "5":
			show_available_images("events")
		
		elif choice == "6":
			validate_all_events(manager)
		
		elif choice == "7":
			cleanup_past_events(manager)
		
		elif choice == "8":
			manager.save()
		
		elif choice == "0":
			break
		
		else:
			print("❌ Invalid choice")


def schedule_menu(manager):
	"""Schedule management submenu"""
	while True:
		print("\n" + "="*80)
		print("📆 SCHEDULE MANAGEMENT")
		print("="*80)
		print("1. List all schedules")
		print("2. Create new schedule")
		print("3. Create from template")  # ← NEW
		print("4. Edit schedule")         # ← Was 3
		print("5. Delete schedule file")  # ← Was 4
		print("6. Show available images") # ← Was 5
		print("7. Validate all schedules")# ← Was 6
		print("8. Clean up old schedules")# ← Was 7
		print("9. Sync default ↔ local")  # ← NEW
		print("10. Save all changes")     # ← Was 8
		print("0. Back to main menu")
		print()
		
		choice = input("Choose option (0-10): ").strip()
		
		if choice == "1":
			manager.list_schedules()
		
		elif choice == "2":
			create_schedule_interactive(manager)
		
		elif choice == "3":  # NEW
			create_from_template_interactive(manager)
		
		elif choice == "4":
			edit_schedule_interactive(manager)
		
		elif choice == "5":
			delete_schedule_file_interactive(manager)
		
		elif choice == "6":
			show_available_images("schedules")
		
		elif choice == "7":
			validate_all_schedules(manager)
		
		elif choice == "8":
			print("\n🗑️  Clean Up Old Schedules")
			days = input("Delete schedules older than how many days? (default=30): ").strip() or "30"
			try:
				manager.cleanup_past_schedules(int(days))
			except ValueError:
				print("❌ Invalid number")
		
		elif choice == "9":  # NEW
			sync_default_and_local(manager)
		
		elif choice == "10":
			manager.save_all()
		
		elif choice == "0":
			break
		
		else:
			print("❌ Invalid choice")


# ============================================================================
# INTERACTIVE HELPERS - EVENTS
# ============================================================================

def add_event_interactive(manager):
	"""Interactive event creation"""
	print("\n➕ Add New Event")
	print("(Type 'cancel' at any prompt to return to menu)\n")
	
	# Date
	date = None
	while date is None:
		date_input = input("Date (YYYY-MM-DD): ").strip()
		if date_input.lower() == 'cancel':
			return
		valid, msg = EventValidator.validate_date(date_input)
		if valid:
			date = date_input
		else:
			print(f"   ❌ {msg}")
	
	# Top Line
	print("\n💡 Top Line = displays on TOP of screen")
	top_line = None
	while top_line is None:
		line_input = input("Top Line (max 12 chars): ").strip()
		if line_input.lower() == 'cancel':
			return
		valid, msg = EventValidator.validate_text(line_input, "Top Line", max_length=12)
		if valid:
			top_line = line_input
		else:
			print(f"   ❌ {msg}")
	
	# Bottom Line
	print("\n💡 Bottom Line = displays on BOTTOM (usually the name)")
	bottom_line = None
	while bottom_line is None:
		line_input = input("Bottom Line (max 12 chars): ").strip()
		if line_input.lower() == 'cancel':
			return
		valid, msg = EventValidator.validate_text(line_input, "Bottom Line", max_length=12)
		if valid:
			bottom_line = line_input
		else:
			print(f"   ❌ {msg}")
	
	# Image
	images = get_available_images("events")
	if images:
		print(f"\nAvailable images ({len(images)} files):")
		for i, img in enumerate(images[:15], 1):
			print(f"  {i:2d}. {img}")
		if len(images) > 15:
			print(f"  ... and {len(images) - 15} more")
		print("Type number, name, or 'list' for all images\n")
	
	image = None
	while image is None:
		img_input = input("Image: ").strip()
		
		if img_input.lower() == 'cancel':
			return
		
		if img_input.lower() == 'list' and images:
			print("\n📋 Complete image list:")
			for i, img in enumerate(images, 1):
				print(f"  {i:2d}. {img}")
			print()
			continue
		
		# Try as number
		try:
			img_index = int(img_input) - 1
			if 0 <= img_index < len(images):
				img_input = images[img_index]
		except ValueError:
			pass
		
		valid, msg = validate_image(img_input, "events")
		if valid:
			image = img_input
		else:
			print(f"   ❌ {msg}")
	
	# Color
	print(f"\n🎨 Available colors:")
	for i, c in enumerate(VALID_COLORS[:16], 1):
		print(f"  {i:2d}. {c}")
	if len(VALID_COLORS) > 16:
		print(f"  ... and {len(VALID_COLORS) - 16} more (type 'list' to see all)")
	
	color = None
	while color is None:
		color_input = input("\nColor (number or name, default=1/MINT): ").strip() or "1"
		
		if color_input.lower() == 'cancel':
			return
		
		if color_input.lower() == 'list':
			print(f"\n🎨 All colors:")
			for i, c in enumerate(VALID_COLORS, 1):
				print(f"  {i:2d}. {c}")
			print()
			continue
		
		# Try as number
		try:
			color_index = int(color_input) - 1
			if 0 <= color_index < len(VALID_COLORS):
				color = VALID_COLORS[color_index]
				continue
		except ValueError:
			pass
		
		valid, msg = validate_color(color_input)
		if valid:
			color = color_input.upper()
		else:
			print(f"   ❌ {msg}")
	
	# Time Window (optional)
	print(f"\n🕐 Time Window (optional)")
	print("   Leave blank for all-day event")
	
	start_hour = None
	end_hour = None
	
	time_input = input("\nAdd time window? (y/n, default=n): ").strip().lower()
	
	if time_input == 'y':
		while start_hour is None:
			start_input = input("Start hour (0-23, e.g., 8 for 8am): ").strip()
			if start_input.lower() == 'cancel' or not start_input:
				break
			valid, msg = EventValidator.validate_time(start_input, "Start hour")
			if valid:
				start_hour = int(start_input)
			else:
				print(f"   ❌ {msg}")
		
		if start_hour is not None:
			while end_hour is None:
				end_input = input(f"End hour ({start_hour+1}-23, e.g., 20 for 8pm): ").strip()
				if end_input.lower() == 'cancel' or not end_input:
					start_hour = None
					break
				valid, msg = EventValidator.validate_time(end_input, "End hour")
				if valid:
					end_val = int(end_input)
					if end_val <= start_hour:
						print("   ❌ End hour must be after start hour")
						continue
					end_hour = end_val
				else:
					print(f"   ❌ {msg}")
	
	# Add event
	manager.add_event(date, top_line, bottom_line, image, color, start_hour, end_hour)


def edit_event_interactive(manager, index):
	"""Interactive event editing (simplified version)"""
	print("\n✏️  Edit Event")
	print("(Press Enter to keep current value, or type new value)")
	print("(Type 'cancel' to abort edit)\n")
	
	old_event = manager.events[index]
	print(f"Editing: {old_event[0]} - {old_event[1]} / {old_event[2]}\n")
	
	# For brevity, just allow editing the most common fields
	# Date
	date = input(f"Date [{old_event[0]}]: ").strip() or old_event[0]
	if date.lower() == 'cancel':
		return
	
	# Top/Bottom lines
	top_line = input(f"Top Line [{old_event[1]}]: ").strip() or old_event[1]
	if top_line.lower() == 'cancel':
		return
	
	bottom_line = input(f"Bottom Line [{old_event[2]}]: ").strip() or old_event[2]
	if bottom_line.lower() == 'cancel':
		return
	
	# Image
	image = input(f"Image [{old_event[3]}]: ").strip() or old_event[3]
	if image.lower() == 'cancel':
		return
	
	# Color
	color = input(f"Color [{old_event[4] if len(old_event) > 4 else 'MINT'}]: ").strip() or (old_event[4] if len(old_event) > 4 else 'MINT')
	if color.lower() == 'cancel':
		return
	
	# Keep time window if it exists
	start_hour = old_event[5] if len(old_event) > 5 else None
	end_hour = old_event[6] if len(old_event) > 6 else None
	
	# Update
	new_event = [date, top_line, bottom_line, image, color.upper()]
	if start_hour:
		new_event.extend([start_hour, end_hour])
	
	manager.events[index] = new_event
	print(f"✓ Event updated")


def validate_all_events(manager):
	"""Validate all events"""
	print("\n🔍 Validating all events...")
	issues = []
	
	for i, event in enumerate(manager.events):
		if len(event) < 5:
			issues.append(f"Event {i}: Incomplete data")
			continue
		
		valid, errors = EventValidator.validate_event(
			event[0], event[1], event[2], event[3], event[4],
			event[5] if len(event) > 5 else None,
			event[6] if len(event) > 6 else None
		)
		
		if not valid:
			issues.append(f"Event {i} ({event[0]}): {', '.join(errors)}")
	
	if issues:
		print("⚠️  Found issues:")
		for issue in issues:
			print(f"   - {issue}")
	else:
		print("✓ All events valid!")


def cleanup_past_events(manager):
	"""Remove past events"""
	today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
	original_count = len(manager.events)
	
	manager.events = [
		event for event in manager.events
		if datetime.strptime(event[0], '%Y-%m-%d') >= today
	]
	
	removed_count = original_count - len(manager.events)
	if removed_count > 0:
		print(f"✓ Removed {removed_count} past events")
	else:
		print("✓ No past events to remove")
		
def check_schedule_overlap(manager, date, days, start_time, end_time, exclude_name=None):
	"""
	Check if a schedule overlaps with existing schedules
	Returns list of overlapping schedules
	"""
	overlaps = []
	
	# Get schedules for this date
	if date not in manager.schedules:
		return overlaps
	
	# Parse new schedule times
	try:
		new_start_h, new_start_m = map(int, start_time.split(':'))
		new_end_h, new_end_m = map(int, end_time.split(':'))
		new_start_mins = new_start_h * 60 + new_start_m
		new_end_mins = new_end_h * 60 + new_end_m
	except:
		return overlaps  # Can't parse times, skip check
	
	# Convert days string to set for comparison
	new_days_set = set(days)
	
	# Check each existing schedule
	for existing in manager.schedules[date]:
		# Skip if this is the schedule we're editing
		if exclude_name and existing['name'] == exclude_name:
			continue
		
		# Check if days overlap
		existing_days_set = set(existing['days'])
		if not new_days_set.intersection(existing_days_set):
			continue  # No overlapping days
		
		# Days overlap, check times
		try:
			exist_start_h = int(existing['start_hour'])
			exist_start_m = int(existing['start_min'])
			exist_end_h = int(existing['end_hour'])
			exist_end_m = int(existing['end_min'])
			
			exist_start_mins = exist_start_h * 60 + exist_start_m
			exist_end_mins = exist_end_h * 60 + exist_end_m
			
			# Check for time overlap
			# Overlaps if: (new_start < exist_end) AND (new_end > exist_start)
			if new_start_mins < exist_end_mins and new_end_mins > exist_start_mins:
				# Get overlapping days
				overlap_days = new_days_set.intersection(existing_days_set)
				overlap_day_names = [DAY_NAMES[d] for d in sorted(overlap_days) if d in DAY_NAMES]
				
				overlaps.append({
					'name': existing['name'],
					'start': f"{exist_start_h}:{str(exist_start_m).zfill(2)}",
					'end': f"{exist_end_h}:{str(exist_end_m).zfill(2)}",
					'days': ','.join(overlap_day_names)
				})
		except:
			pass  # Skip if can't parse existing schedule
	
	return overlaps
	
def sync_default_and_local(manager):
	"""Sync between default.csv and local schedules.csv"""
	print("\n🔄 Sync Default ↔ Local Schedule Files")
	print("="*80)
	
	default_file = SCHEDULES_FOLDER / "default.csv"
	local_file = SCHEDULES_FOLDER / "schedules.csv"
	
	# Check if files exist
	default_exists = default_file.exists()
	local_exists = local_file.exists()
	
	if not default_exists and not local_exists:
		print("❌ Neither default.csv nor schedules.csv exists")
		return
	
	# Get modification times
	if default_exists:
		default_mtime = default_file.stat().st_mtime
		default_time = datetime.fromtimestamp(default_mtime)
		print(f"📄 default.csv:    Last modified {default_time.strftime('%Y-%m-%d %H:%M:%S')}")
	else:
		print(f"📄 default.csv:    Does not exist")
		default_mtime = 0
	
	if local_exists:
		local_mtime = local_file.stat().st_mtime
		local_time = datetime.fromtimestamp(local_mtime)
		print(f"📄 schedules.csv:  Last modified {local_time.strftime('%Y-%m-%d %H:%M:%S')}")
	else:
		print(f"📄 schedules.csv:  Does not exist")
		local_mtime = 0
	
	# Determine which is newer
	if not default_exists:
		print("\n→ Will create default.csv from schedules.csv")
		action = "local_to_default"
	elif not local_exists:
		print("\n→ Will create schedules.csv from default.csv")
		action = "default_to_local"
	elif default_mtime > local_mtime:
		age_diff = (default_mtime - local_mtime) / 60  # minutes
		print(f"\n→ default.csv is newer (by {age_diff:.0f} minutes)")
		print("   Will update schedules.csv from default.csv")
		action = "default_to_local"
	elif local_mtime > default_mtime:
		age_diff = (local_mtime - default_mtime) / 60  # minutes
		print(f"\n→ schedules.csv is newer (by {age_diff:.0f} minutes)")
		print("   Will update default.csv from schedules.csv")
		action = "local_to_default"
	else:
		print("\n✓ Files are already in sync!")
		return
	
	# Confirm
	confirm = input("\nProceed with sync? (y/n): ").strip().lower()
	
	if confirm != 'y':
		print("Sync cancelled")
		return
	
	# Perform sync
	try:
		import shutil
		
		if action == "default_to_local":
			shutil.copy2(default_file, local_file)
			print(f"✓ Copied default.csv → schedules.csv")
			
			# Also update in-memory
			if 'default' in manager.schedules:
				manager.schedules['local'] = manager.schedules['default'].copy()
		
		elif action == "local_to_default":
			shutil.copy2(local_file, default_file)
			print(f"✓ Copied schedules.csv → default.csv")
			
			# Also update in-memory
			if 'local' in manager.schedules:
				manager.schedules['default'] = manager.schedules['local'].copy()
		
		print("\n✅ Sync complete!")
		print("💡 Remember to push to GitHub to sync with devices")
		
	except Exception as e:
		print(f"❌ Sync failed: {e}")


# ============================================================================
# INTERACTIVE HELPERS - SCHEDULES
# ============================================================================

def create_schedule_interactive(manager):
	"""Interactive schedule creation"""
	print("\n➕ Create New Schedule")
	print("(Type 'cancel' at any prompt to return)\n")
	
	# Date
	print("📅 Schedule Type:")
	print("  1. Date-specific (e.g., 2025-12-25 for Christmas)")
	print("  2. Default (fallback for all days)")
	
	date_type = input("\nChoose (1/2): ").strip()
	
	if date_type == '2':
		date = 'default'
		is_default = True
		print("✓ Creating default schedule")
	else:
		date = None
		is_default = False
		while date is None:
			date_input = input("\nEnter date (YYYY-MM-DD): ").strip()
			if date_input.lower() == 'cancel':
				return
			valid, msg = ScheduleValidator.validate_schedule_date(date_input)
			if valid:
				date = date_input
			else:
				print(f"   ❌ {msg}")
	
	# Name
	name = None
	while name is None:
		name_input = input("\nSchedule Name (e.g., 'Morning Routine'): ").strip()
		if name_input.lower() == 'cancel':
			return
		valid, msg = ScheduleValidator.validate_schedule_name(name_input)
		if valid:
			name = name_input
		else:
			print(f"   ❌ {msg}")
	
	# Days - AUTO-SET for date-specific, ASK for default
	if is_default:
		print("\n📆 Days (1=Monday, 7=Sunday):")
		print("  Examples: '12345' = Mon-Fri")
		print("           '67' = Sat-Sun")
		print("           '1234567' = All days")
		
		days = None
		while days is None:
			days_input = input("\nDays: ").strip()
			if days_input.lower() == 'cancel':
				return
			valid, msg = ScheduleValidator.validate_days(days_input)
			if valid:
				days = days_input
			else:
				print(f"   ❌ {msg}")
	else:
		# AUTO-SET days based on date
		try:
			date_obj = datetime.strptime(date, '%Y-%m-%d')
			# Python weekday: 0=Monday, 6=Sunday
			# Our format: 1=Monday, 7=Sunday
			day_num = str(date_obj.weekday() + 1)
			days = day_num
			day_name = DAY_NAMES[day_num]
			print(f"\n✓ Auto-set days to {day_name} (day {day_num}) based on {date}")
		except:
			# Fallback to all days if date parsing fails
			days = "1234567"
			print("\n✓ Auto-set days to all days (1234567)")
	
	# Start Time
	start_time = None
	while start_time is None:
		start_input = input("\nStart Time (HH:MM, e.g., 07:00): ").strip()
		if start_input.lower() == 'cancel':
			return
		valid, msg = ScheduleValidator.validate_time_format(start_input)
		if valid:
			start_time = start_input
		else:
			print(f"   ❌ {msg}")
	
	# End Time
	end_time = None
	while end_time is None:
		end_input = input("End Time (HH:MM, e.g., 07:30): ").strip()
		if end_input.lower() == 'cancel':
			return
		valid, msg = ScheduleValidator.validate_time_format(end_input)
		if not valid:
			print(f"   ❌ {msg}")
			continue
		
		valid, msg = ScheduleValidator.validate_time_range(start_time, end_input)
		if valid:
			end_time = end_input
		else:
			print(f"   ❌ {msg}")
	
	# Image
	images = get_available_images("schedules")
	if images:
		print(f"\nAvailable images ({len(images)} files):")
		for i, img in enumerate(images[:15], 1):
			print(f"  {i:2d}. {img}")
		if len(images) > 15:
			print(f"  ... and {len(images) - 15} more")
		print("Type number, name, or 'list' for all\n")
	
	image = None
	while image is None:
		img_input = input("Image filename: ").strip()
		
		if img_input.lower() == 'cancel':
			return
		
		if img_input.lower() == 'list' and images:
			print("\n📋 Complete image list:")
			for i, img in enumerate(images, 1):
				print(f"  {i:2d}. {img}")
			print()
			continue
		
		# Try as number
		try:
			img_index = int(img_input) - 1
			if 0 <= img_index < len(images):
				img_input = images[img_index]
		except ValueError:
			pass
		
		valid, msg = validate_image(img_input, "schedules")
		if valid:
			image = img_input
		else:
			print(f"   ❌ {msg}")
	
	# Progress bar
	progress_input = input("\nShow progress bar? (y/n, default=y): ").strip().lower()
	progressbar = progress_input != 'n'
	
	# Check for overlaps BEFORE showing preview
	overlaps = check_schedule_overlap(manager, date, days, start_time, end_time, exclude_name=None)
	
	# Preview
	if is_default:
		day_names = [DAY_NAMES[d] for d in days if d in DAY_NAMES]
		days_display = ', '.join(day_names)
	else:
		days_display = DAY_NAMES.get(days, days)
	
	print(f"\n📋 Preview:")
	print(f"  Date: {date}")
	print(f"  Name: {name}")
	print(f"  Days: {days_display}")
	print(f"  Time: {start_time} - {end_time}")
	print(f"  Image: {image}")
	print(f"  Progress: {'Yes' if progressbar else 'No'}")
	
	# Show overlap warnings
	if overlaps:
		print(f"\n⚠️  WARNING: This schedule overlaps with {len(overlaps)} existing schedule(s):")
		for overlap in overlaps:
			print(f"     - {overlap['name']}: {overlap['start']}-{overlap['end']} on {overlap['days']}")
		print("\n   Overlapping schedules may cause conflicts!")
	
	confirm = input("\nSave schedule? (y/n): ").strip().lower()
	if confirm == 'y':
		manager.add_schedule(date, name, days, start_time, end_time, image, progressbar)
	else:
		print("Cancelled")
		
def create_from_template_interactive(manager):
	"""Create a new schedule file based on a template"""
	print("\n📋 Create Schedule From Template")
	print("="*80)
	
	# Show available templates
	print("\nAvailable templates:")
	print("  1. Default schedule (all schedules from default.csv)")
	print("  2. Copy from another date")
	print("  3. Copy from local device file (schedules/schedules.csv)")
	print("  0. Cancel")
	
	template_choice = input("\nChoose template (0-3): ").strip()
	
	if template_choice == "0":
		return
	
	# Get target date
	target_date = None
	while target_date is None:
		date_input = input("\nTarget date for new schedule (YYYY-MM-DD): ").strip()
		if date_input.lower() == 'cancel':
			return
		valid, msg = ScheduleValidator.validate_schedule_date(date_input)
		if valid and date_input != 'default':
			target_date = date_input
		else:
			print(f"   ❌ {msg if not valid else 'Cannot use default as target'}")
	
	# Get target day of week
	try:
		target_date_obj = datetime.strptime(target_date, '%Y-%m-%d')
		target_day = str(target_date_obj.weekday() + 1)  # 1=Monday, 7=Sunday
		target_day_name = DAY_NAMES[target_day]
		print(f"✓ Target date is a {target_day_name} (day {target_day})")
	except:
		print("❌ Invalid date")
		return
	
	# Load template based on choice
	template_schedules = []
	
	if template_choice == "1":
		# Use default.csv
		if 'default' not in manager.schedules:
			print("❌ No default schedule found")
			return
		
		# Filter schedules that apply to target day
		for schedule in manager.schedules['default']:
			if target_day in schedule['days']:
				template_schedules.append(schedule.copy())
		
		print(f"\n✓ Found {len(template_schedules)} schedule(s) from default that apply to {target_day_name}")
	
	elif template_choice == "2":
		# Copy from another date
		manager.list_schedules()
		
		source_date = input("\nSource date (YYYY-MM-DD) or 'default': ").strip()
		
		if source_date not in manager.schedules:
			print(f"❌ No schedule found for {source_date}")
			return
		
		# If copying from default, filter by day
		if source_date == 'default':
			for schedule in manager.schedules['default']:
				if target_day in schedule['days']:
					template_schedules.append(schedule.copy())
			print(f"✓ Found {len(template_schedules)} schedule(s) that apply to {target_day_name}")
		else:
			# Copy all schedules from that date
			template_schedules = [s.copy() for s in manager.schedules[source_date]]
			print(f"✓ Copying {len(template_schedules)} schedule(s) from {source_date}")
	
	elif template_choice == "3":
		# Load from local device file
		local_file = SCHEDULES_FOLDER / "schedules.csv"
		
		if not local_file.exists():
			print(f"❌ Local file not found: {local_file}")
			return
		
		# Load the local file
		local_schedules = manager._load_schedule_file(local_file)
		
		# Filter by target day
		for schedule in local_schedules:
			if target_day in schedule['days']:
				template_schedules.append(schedule.copy())
		
		print(f"✓ Found {len(template_schedules)} schedule(s) from local file that apply to {target_day_name}")
	
	else:
		print("❌ Invalid choice")
		return
	
	# Check if we have any schedules
	if not template_schedules:
		print(f"❌ No schedules found for {target_day_name} in selected template")
		return
	
	# Preview template schedules
	print(f"\n📋 Template schedules to copy:")
	print("-" * 80)
	for i, schedule in enumerate(template_schedules):
		start = f"{schedule['start_hour']}:{schedule['start_min'].zfill(2)}"
		end = f"{schedule['end_hour']}:{schedule['end_min'].zfill(2)}"
		print(f"  {i+1}. {schedule['name']:25s} | {start}-{end} | {schedule['image']}")
	print("-" * 80)
	
	# Options for modification
	print("\nOptions:")
	print("  1. Copy all schedules as-is")
	print("  2. Copy all with time adjustment (shift all schedules)")
	print("  3. Select which schedules to copy")
	print("  0. Cancel")
	
	mod_choice = input("\nChoose option (0-3): ").strip()
	
	if mod_choice == "0":
		return
	
	elif mod_choice == "1":
		# Copy as-is
		selected_schedules = template_schedules
	
	elif mod_choice == "2":
		# Time adjustment
		print("\n⏰ Time Adjustment")
		print("Enter time shift (e.g., +30 for 30 min later, -15 for 15 min earlier)")
		
		try:
			shift_input = input("Shift (minutes): ").strip()
			shift_minutes = int(shift_input)
			
			selected_schedules = []
			for schedule in template_schedules:
				adjusted = schedule.copy()
				
				# Adjust start time
				start_mins = int(adjusted['start_hour']) * 60 + int(adjusted['start_min'])
				start_mins += shift_minutes
				adjusted['start_hour'] = str(start_mins // 60)
				adjusted['start_min'] = str(start_mins % 60)
				
				# Adjust end time
				end_mins = int(adjusted['end_hour']) * 60 + int(adjusted['end_min'])
				end_mins += shift_minutes
				adjusted['end_hour'] = str(end_mins // 60)
				adjusted['end_min'] = str(end_mins % 60)
				
				selected_schedules.append(adjusted)
			
			print(f"✓ Adjusted all times by {shift_minutes:+d} minutes")
			
		except ValueError:
			print("❌ Invalid shift value")
			return
	
	elif mod_choice == "3":
		# Select specific schedules
		print("\nEnter schedule numbers to copy (comma-separated, e.g., 1,3,5):")
		selection = input("Schedules: ").strip()
		
		try:
			indices = [int(x.strip()) - 1 for x in selection.split(',')]
			selected_schedules = [template_schedules[i] for i in indices if 0 <= i < len(template_schedules)]
			
			if not selected_schedules:
				print("❌ No valid schedules selected")
				return
			
			print(f"✓ Selected {len(selected_schedules)} schedule(s)")
			
		except:
			print("❌ Invalid selection")
			return
	
	else:
		print("❌ Invalid choice")
		return
	
	# Update days to match target day (date-specific schedules should only run on that day)
	for schedule in selected_schedules:
		schedule['days'] = target_day
	
	# Final confirmation
	print(f"\n📋 Ready to create schedule for {target_date} ({target_day_name})")
	print(f"   {len(selected_schedules)} schedule(s) will be added")
	
	# Check if target date already has schedules
	if target_date in manager.schedules and manager.schedules[target_date]:
		print(f"\n⚠️  WARNING: {target_date} already has {len(manager.schedules[target_date])} schedule(s)")
		print("   Options:")
		print("     1. Replace existing schedules")
		print("     2. Merge with existing schedules")
		print("     0. Cancel")
		
		replace_choice = input("\n   Choose (0-2): ").strip()
		
		if replace_choice == "0":
			return
		elif replace_choice == "1":
			manager.schedules[target_date] = selected_schedules
			print(f"✓ Replaced schedules for {target_date}")
		elif replace_choice == "2":
			manager.schedules[target_date].extend(selected_schedules)
			print(f"✓ Merged schedules for {target_date}")
		else:
			print("❌ Invalid choice")
			return
	else:
		# No existing schedules, just add
		manager.schedules[target_date] = selected_schedules
		print(f"✓ Created schedule for {target_date}")
	
	print(f"\n✅ Schedule file created! Remember to save (option 10) and push to GitHub (option 3 from main menu)")


def check_schedule_overlap(manager, date, days, start_time, end_time, exclude_name=None):
	"""
	Check if a schedule overlaps with existing schedules
	Returns list of overlapping schedules
	"""
	overlaps = []
	
	# Get schedules for this date
	if date not in manager.schedules:
		return overlaps
	
	# Parse new schedule times
	try:
		new_start_h, new_start_m = map(int, start_time.split(':'))
		new_end_h, new_end_m = map(int, end_time.split(':'))
		new_start_mins = new_start_h * 60 + new_start_m
		new_end_mins = new_end_h * 60 + new_end_m
	except:
		return overlaps  # Can't parse times, skip check
	
	# Convert days string to set for comparison
	new_days_set = set(days)
	
	# Check each existing schedule
	for existing in manager.schedules[date]:
		# Skip if this is the schedule we're editing
		if exclude_name and existing['name'] == exclude_name:
			continue
		
		# Check if days overlap
		existing_days_set = set(existing['days'])
		if not new_days_set.intersection(existing_days_set):
			continue  # No overlapping days
		
		# Days overlap, check times
		try:
			exist_start_h = int(existing['start_hour'])
			exist_start_m = int(existing['start_min'])
			exist_end_h = int(existing['end_hour'])
			exist_end_m = int(existing['end_min'])
			
			exist_start_mins = exist_start_h * 60 + exist_start_m
			exist_end_mins = exist_end_h * 60 + exist_end_m
			
			# Check for time overlap
			# Overlaps if: (new_start < exist_end) AND (new_end > exist_start)
			if new_start_mins < exist_end_mins and new_end_mins > exist_start_mins:
				# Get overlapping days
				overlap_days = new_days_set.intersection(existing_days_set)
				overlap_day_names = [DAY_NAMES[d] for d in sorted(overlap_days) if d in DAY_NAMES]
				
				overlaps.append({
					'name': existing['name'],
					'start': f"{exist_start_h}:{str(exist_start_m).zfill(2)}",
					'end': f"{exist_end_h}:{str(exist_end_m).zfill(2)}",
					'days': ','.join(overlap_day_names)
				})
		except:
			pass  # Skip if can't parse existing schedule
	
	return overlaps
	
def edit_schedule_interactive(manager):
	"""Interactive schedule editing"""
	print("\n✏️  Edit Schedule")
	
	manager.list_schedules()
	
	if not manager.schedules:
		print("❌ No schedules to edit")
		return
	
	date = input("\nEnter date (YYYY-MM-DD) or 'default': ").strip()
	
	if date not in manager.schedules:
		print(f"❌ No schedule found for {date}")
		return
	
	schedule_list = manager.schedules[date]
	
	if len(schedule_list) == 1:
		index = 0
	else:
		print(f"\n{len(schedule_list)} schedules on {date}:")
		for i, sch in enumerate(schedule_list):
			print(f"  {i}. {sch['name']}")
		
		try:
			index = int(input("\nChoose schedule number: "))
			if not (0 <= index < len(schedule_list)):
				print("❌ Invalid number")
				return
		except ValueError:
			print("❌ Invalid number")
			return
	
	schedule = schedule_list[index]
	original_name = schedule['name']
	
	print(f"\nEditing: {schedule['name']}")
	print("(Press Enter to keep current value)\n")
	
	# Edit fields
	schedule['name'] = input(f"Name [{schedule['name']}]: ").strip() or schedule['name']
	schedule['days'] = input(f"Days [{schedule['days']}]: ").strip() or schedule['days']
	
	start = f"{schedule['start_hour']}:{schedule['start_min'].zfill(2)}"
	schedule_start_new = input(f"Start Time [{start}]: ").strip() or start
	if ':' in schedule_start_new:
		h, m = schedule_start_new.split(':')
		schedule['start_hour'] = h
		schedule['start_min'] = m
	
	end = f"{schedule['end_hour']}:{schedule['end_min'].zfill(2)}"
	schedule_end_new = input(f"End Time [{end}]: ").strip() or end
	if ':' in schedule_end_new:
		h, m = schedule_end_new.split(':')
		schedule['end_hour'] = h
		schedule['end_min'] = m
	
	schedule['image'] = input(f"Image [{schedule['image']}]: ").strip() or schedule['image']
	
	enabled_str = "y" if schedule['enabled'] == '1' else "n"
	enabled_new = input(f"Enabled? (y/n) [{enabled_str}]: ").strip().lower() or enabled_str
	schedule['enabled'] = '1' if enabled_new == 'y' else '0'
	
	# Check for overlaps (exclude current schedule from check)
	overlaps = check_schedule_overlap(
		manager, date, schedule['days'],
		f"{schedule['start_hour']}:{schedule['start_min'].zfill(2)}",
		f"{schedule['end_hour']}:{schedule['end_min'].zfill(2)}",
		exclude_name=original_name
	)
	
	if overlaps:
		print(f"\n⚠️  WARNING: This schedule now overlaps with {len(overlaps)} other schedule(s):")
		for overlap in overlaps:
			print(f"     - {overlap['name']}: {overlap['start']}-{overlap['end']} on {overlap['days']}")
		
		confirm = input("\nSave anyway? (y/n): ").strip().lower()
		if confirm != 'y':
			print("Edit cancelled")
			return
	
	print("✓ Schedule updated")


def delete_schedule_file_interactive(manager):
	"""Interactive schedule file deletion"""
	print("\n🗑️  Delete Schedule File")
	
	manager.list_schedules()
	
	if not manager.schedules:
		print("❌ No schedules to delete")
		return
	
	date = input("\nEnter date (YYYY-MM-DD) or 'default' to delete: ").strip()
	
	if date not in manager.schedules:
		print(f"❌ No schedule found for {date}")
		return
	
	schedule_count = len(manager.schedules[date])
	confirm = input(f"⚠️  Delete {schedule_count} schedule(s) for {date}? (y/n): ").strip().lower()
	
	if confirm == 'y':
		manager.delete_schedule_file(date)
	else:
		print("Cancelled")


def validate_all_schedules(manager):
	"""Validate all schedules"""
	print("\n🔍 Validating all schedules...")
	issues = []
	
	for date_key, schedule_list in manager.schedules.items():
		for i, schedule in enumerate(schedule_list):
			try:
				name = schedule['name']
				days = schedule['days']
				start_time = f"{schedule['start_hour']}:{schedule['start_min'].zfill(2)}"
				end_time = f"{schedule['end_hour']}:{schedule['end_min'].zfill(2)}"
				image = schedule['image']
				
				valid, errors = ScheduleValidator.validate_schedule(name, days, start_time, end_time, image)
				
				if not valid:
					issues.append(f"{date_key} - {name}: {', '.join(errors)}")
			except Exception as e:
				issues.append(f"{date_key} - Schedule {i}: {e}")
	
	if issues:
		print("⚠️  Found issues:")
		for issue in issues:
			print(f"   - {issue}")
	else:
		print("✓ All schedules valid!")


def show_available_images(image_type):
	"""Display all available images"""
	images = get_available_images(image_type)
	folder = EVENTS_IMAGES_FOLDER if image_type == "events" else SCHEDULES_IMAGES_FOLDER
	
	if not images:
		print(f"\n⚠️  No images found in: {folder}")
		print("Update paths in the script configuration")
		return
	
	print(f"\n🖼️  Available {image_type.title()} Images ({len(images)} files):")
	print(f"    Folder: {folder}")
	print("-" * 60)
	for i, img in enumerate(images, 1):
		print(f"{i:3d}. {img}")
	print("-" * 60)


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
	# Check configuration
	if not PROJECT_ROOT.exists():
		print("\n" + "="*80)
		print("⚠️  SETUP REQUIRED")
		print("="*80)
		print(f"Project folder not found: {PROJECT_ROOT}")
		print("\nEdit this script and update PROJECT_ROOT to point to your SCREENY folder")
		print("\nExample:")
		print('  PROJECT_ROOT = Path.home() / "Documents" / "SCREENY"')
		print("="*80)
		input("\nPress Enter to continue anyway...")
	
	main_menu()