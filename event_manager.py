#!/usr/bin/env python3
"""
Pantallita Event Manager
Creates and validates ephemeral events for your display screens
Automatically detects available images from local folder
"""
import csv
import re
import subprocess
from datetime import datetime
from pathlib import Path

# Valid colors for events
VALID_COLORS = [
	"MINT", "BUGAMBILIA", "LILAC", "RED", "GREEN", "BLUE",
	"ORANGE", "YELLOW", "CYAN", "PURPLE", "PINK", "AQUA", "WHITE"
]

# Path to your local Pantallita images folder
# CHANGE THIS to match your setup
IMAGES_FOLDER = Path.home() / "Documents" / "Adafruit" / "SCREENY V2.0" / "img" / "events"


class EventValidator:
	"""Validates event data"""
	
	@staticmethod
	def get_available_images():
		"""Scan the local images folder for .bmp files"""
		if not IMAGES_FOLDER.exists():
			print(f"⚠️  Warning: Images folder not found: {IMAGES_FOLDER}")
			print(f"   Update IMAGES_FOLDER path in script")
			return []
		
		# Find all .bmp files in the folder
		bmp_files = sorted([f.name for f in IMAGES_FOLDER.glob("*.bmp")])
		return bmp_files
	
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
	def validate_image(image_name):
		"""Validate image file name against available images"""
		available_images = EventValidator.get_available_images()
		
		if not available_images:
			# If can't read folder, just check format
			if not image_name.endswith('.bmp'):
				return False, "Image must be a .bmp file"
			return True, "OK (couldn't verify against local folder)"
		
		if image_name not in available_images:
			return False, f"Image '{image_name}' not found in {IMAGES_FOLDER}"
		
		return True, "OK"
	
	@staticmethod
	def validate_color(color):
		"""Validate color name"""
		color_upper = color.upper()
		if color_upper not in VALID_COLORS:
			return False, f"Color must be one of: {', '.join(VALID_COLORS)}"
		
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
		
		# Validate each field
		valid, msg = cls.validate_date(date)
		if not valid:
			errors.append(f"Date: {msg}")
		
		valid, msg = cls.validate_text(top_line, "Top Line", max_length=12)
		if not valid:
			errors.append(msg)
		
		valid, msg = cls.validate_text(bottom_line, "Bottom Line", max_length=12)
		if not valid:
			errors.append(msg)
		
		valid, msg = cls.validate_image(image)
		if not valid:
			errors.append(msg)
		
		valid, msg = cls.validate_color(color)
		if not valid:
			errors.append(msg)
		
		# Validate optional time window
		if start_hour is not None:
			valid, msg = cls.validate_time(start_hour, "Start hour")
			if not valid:
				errors.append(msg)
		
		if end_hour is not None:
			valid, msg = cls.validate_time(end_hour, "End hour")
			if not valid:
				errors.append(msg)
		
		# Validate time range logic
		if start_hour is not None and end_hour is not None:
			try:
				if int(start_hour) >= int(end_hour):
					errors.append("Start hour must be before end hour")
			except ValueError:
				pass  # Already caught above
		
		return len(errors) == 0, errors


class EventManager:
	"""Manages ephemeral events"""
	
	def __init__(self, filename="ephemeral_events.csv"):
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
		# Validate
		valid, errors = EventValidator.validate_event(date, top_line, bottom_line, image, color, start_hour, end_hour)
		
		if not valid:
			print("❌ Validation failed:")
			for error in errors:
				print(f"   - {error}")
			return False
		
		# Build event list
		event = [date, top_line, bottom_line, image, color.upper()]
		
		# Add optional time window
		if start_hour is not None and end_hour is not None:
			event.append(str(start_hour))
			event.append(str(end_hour))
		
		self.events.append(event)
		
		# Show what was added
		time_info = f" ({start_hour}:00-{end_hour}:00)" if start_hour is not None else " (all day)"
		print(f"✓ Added: {date} - {top_line} / {bottom_line}{time_info}")
		return True
	
	def remove_event(self, index):
		"""Remove event by index"""
		if 0 <= index < len(self.events):
			removed = self.events.pop(index)
			print(f"✓ Removed: {removed[0]} - {removed[1]} / {removed[2]}")
			return True
		else:
			print(f"❌ Invalid index: {index}")
			return False
	
	def list_events(self):
		"""List all events"""
		if not self.events:
			print("No events found.")
			return
		
		# Separate past and future events
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
				future_events.append((i, event))  # If can't parse, assume future
		
		print("\n📅 Current Events:")
		print("=" * 90)
		
		if future_events:
			print("\n🔮 FUTURE EVENTS (will be imported):")
			print("-" * 90)
			for i, event in future_events:
				date = event[0]
				top_line = event[1]
				bottom_line = event[2]
				image = event[3]
				color = event[4] if len(event) > 4 else "MINT"
				
				# Show time window if present
				if len(event) >= 7:
					time_str = f" [{event[5]}:00-{event[6]}:00]"
				else:
					time_str = " [all day]"
				
				print(f"{i:2d}. {date} | {top_line:12s} / {bottom_line:12s} | {image:20s} | {color:10s}{time_str}")
		
		if past_events:
			print("\n📜 PAST EVENTS (will be skipped):")
			print("-" * 90)
			for i, event in past_events:
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
		
		print("=" * 90)
		print(f"Total: {len(self.events)} events ({len(future_events)} future, {len(past_events)} past)\n")
	
	def save(self):
		"""Save events to CSV"""
		# Sort events by date
		self.events.sort(key=lambda x: x[0])
		
		with open(self.filename, 'w', newline='') as f:
			# Write header comments directly (not through CSV writer)
			f.write('# Ephemeral Events - Auto-generated\n')
			f.write('# Format: YYYY-MM-DD,TopLine,BottomLine,Image,Color[,StartHour,EndHour]\n')
			f.write('# TopLine = displays on TOP of screen\n')
			f.write('# BottomLine = displays on BOTTOM (usually the name)\n')
			f.write('# Times are optional (24-hour format, 0-23). If omitted, event shows all day.\n')
			
			# Now use CSV writer for actual data
			writer = csv.writer(f)
			for event in self.events:
				writer.writerow(event)
		
		print(f"✓ Saved {len(self.events)} events to {self.filename}")
	
	def validate_all(self):
		"""Validate all existing events"""
		print("\n🔍 Validating all events...")
		issues = []
		
		for i, event in enumerate(self.events):
			if len(event) < 5:
				issues.append(f"Event {i}: Incomplete data")
				continue
			
			date = event[0]
			top_line = event[1]
			bottom_line = event[2]
			image = event[3]
			color = event[4]
			start_hour = event[5] if len(event) > 5 else None
			end_hour = event[6] if len(event) > 6 else None
			
			valid, errors = EventValidator.validate_event(date, top_line, bottom_line, image, color, start_hour, end_hour)
			
			if not valid:
				issues.append(f"Event {i} ({date}): {', '.join(errors)}")
		
		if issues:
			print("⚠️  Found issues (some may be past events):")
			for issue in issues:
				print(f"   - {issue}")
			return False
		else:
			print("✓ All events valid!")
			return True
	
	def cleanup_past_events(self):
		"""Remove events that are in the past"""
		today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
		original_count = len(self.events)
		
		self.events = [
			event for event in self.events
			if datetime.strptime(event[0], '%Y-%m-%d') >= today
		]
		
		removed_count = original_count - len(self.events)
		if removed_count > 0:
			print(f"✓ Removed {removed_count} past events")
		else:
			print("✓ No past events to remove")
		
		return removed_count > 0
	
	def git_push(self):
		"""Push changes to GitHub"""
		try:
			# Check if git is available
			result = subprocess.run(['git', 'status'], capture_output=True, text=True)
			if result.returncode != 0:
				print("❌ Not a git repository or git not installed")
				return False
			
			# Add the CSV file
			subprocess.run(['git', 'add', self.filename], check=True)
			
			# Commit
			commit_msg = f"Update events - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
			subprocess.run(['git', 'commit', '-m', commit_msg], check=True)
			
			# Push
			print("\n📤 Pushing to GitHub...")
			result = subprocess.run(['git', 'push'], capture_output=True, text=True)
			
			if result.returncode == 0:
				print("✓ Successfully pushed to GitHub!")
				print("\n💡 Your Pantallita screens will fetch updates:")
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
			
	def git_pull(self):
		"""Pull latest changes from GitHub"""
		try:
			print("\n📥 Pulling latest from GitHub...")
			
			# First, check if we need to configure pull strategy
			config_check = subprocess.run(
				['git', 'config', 'pull.rebase'],
				capture_output=True,
				text=True
			)
			
			# If not configured, set to merge (safest for this use case)
			if config_check.returncode != 0:
				print("  Configuring git pull strategy (merge)...")
				subprocess.run(
					['git', 'config', 'pull.rebase', 'false'],
					capture_output=True
				)
			
			# Now pull with merge strategy
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
				# Check if it's a merge conflict
				if "CONFLICT" in result.stdout or "CONFLICT" in result.stderr:
					print("❌ Merge conflict detected!")
					print("\n🔧 To resolve:")
					print("   1. Open your terminal in the events folder")
					print("   2. Run: git status")
					print("   3. Resolve conflicts in ephemeral_events.csv")
					print("   4. Run: git add ephemeral_events.csv")
					print("   5. Run: git commit -m 'Resolved conflicts'")
					print("   6. Then run this tool again")
				else:
					print(f"❌ Pull failed: {result.stderr}")
				return False
				
		except subprocess.CalledProcessError as e:
			print(f"❌ Git error: {e}")
			return False
		except FileNotFoundError:
			print("❌ Git not found")
			return False
			
	def review_and_edit(self):
		"""Review events before pushing, with option to edit"""
		if not self.events:
			print("No events to review.")
			return False
		
		# Separate past and future events
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
		
		print("\n" + "="*90)
		print("📋 REVIEW EVENTS BEFORE PUSHING")
		print("="*90)
		
		if future_events:
			print(f"\n✅ FUTURE EVENTS ({len(future_events)} will be imported by Pantallita):")
			print("-" * 90)
			for i, event in future_events:
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
		
		if past_events:
			print(f"\n⏳ PAST EVENTS ({len(past_events)} will be skipped by Pantallita):")
			print("-" * 90)
			for i, event in past_events:
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
		
		print("="*90)
		print(f"\n📊 Summary:")
		print(f"   Total events: {len(self.events)}")
		print(f"   Future events (will import): {len(future_events)}")
		print(f"   Past events (will skip): {len(past_events)}")
		
		# Ask what to do
		while True:
			print("\n🔧 Options:")
			print("  1. Looks good - proceed with push")
			print("  2. Edit an event")
			print("  3. Remove an event")
			print("  4. Remove all past events")
			print("  5. Cancel - go back to main menu")
			
			choice = input("\nChoose option (1-5): ").strip()
			
			if choice == "1":
				return True  # Proceed with push
			
			elif choice == "2":
				# Edit event
				try:
					event_num = int(input("\nEnter event number to edit: "))
					if 0 <= event_num < len(self.events):
						self.edit_event(event_num)
						# Show updated list
						return self.review_and_edit()  # Recursive call to show updates
					else:
						print("❌ Invalid event number")
				except ValueError:
					print("❌ Invalid number")
			
			elif choice == "3":
				# Remove event
				try:
					event_num = int(input("\nEnter event number to remove: "))
					self.remove_event(event_num)
					# Show updated list
					return self.review_and_edit()  # Recursive call to show updates
				except ValueError:
					print("❌ Invalid number")
			
			elif choice == "4":
				# Remove all past events
				if past_events:
					confirm = input(f"\n⚠️  Remove all {len(past_events)} past events? (y/n): ").strip().lower()
					if confirm == 'y':
						self.cleanup_past_events()
						return self.review_and_edit()  # Show updated list
				else:
					print("ℹ️  No past events to remove")
			
			elif choice == "5":
				return False  # Cancel push
			
			else:
				print("❌ Invalid choice")
	
	def edit_event(self, index):
		"""Edit an existing event"""
		if not (0 <= index < len(self.events)):
			print("❌ Invalid event index")
			return False
		
		old_event = self.events[index]
		print(f"\n✏️  Editing event: {old_event[0]} - {old_event[1]} / {old_event[2]}")
		print("Press Enter to keep current value, or type new value\n")
		
		# Date
		date = None
		while date is None:
			current = old_event[0]
			date_input = input(f"Date [{current}]: ").strip() or current
			if date_input.lower() == 'cancel':
				print("Edit cancelled")
				return False
			valid, msg = EventValidator.validate_date(date_input)
			if valid:
				date = date_input
			else:
				print(f"   ❌ {msg}")
		
		# Top Line
		top_line = None
		while top_line is None:
			current = old_event[1]
			line_input = input(f"Top Line [{current}]: ").strip() or current
			if line_input.lower() == 'cancel':
				print("Edit cancelled")
				return False
			valid, msg = EventValidator.validate_text(line_input, "Top Line", max_length=12)
			if valid:
				top_line = line_input
			else:
				print(f"   ❌ {msg}")
		
		# Bottom Line
		bottom_line = None
		while bottom_line is None:
			current = old_event[2]
			line_input = input(f"Bottom Line [{current}]: ").strip() or current
			if line_input.lower() == 'cancel':
				print("Edit cancelled")
				return False
			valid, msg = EventValidator.validate_text(line_input, "Bottom Line", max_length=12)
			if valid:
				bottom_line = line_input
			else:
				print(f"   ❌ {msg}")
		
		# Image
		images = EventValidator.get_available_images()
		image = None
		while image is None:
			current = old_event[3]
			print(f"\n(Type 'list' to see all images)")
			img_input = input(f"Image [{current}]: ").strip() or current
			
			if img_input.lower() == 'cancel':
				print("Edit cancelled")
				return False
			
			if img_input.lower() == 'list' and images:
				print("\n📋 Available images:")
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
			
			valid, msg = EventValidator.validate_image(img_input)
			if valid:
				image = img_input
			else:
				print(f"   ❌ {msg}")
		
		# Color
		print(f"\n🎨 Available colors:")
		for i, c in enumerate(VALID_COLORS, 1):
			print(f"  {i:2d}. {c}")
		
		color = None
		while color is None:
			current = old_event[4] if len(old_event) > 4 else "MINT"
			color_input = input(f"\nColor (number or name) [{current}]: ").strip() or current
			
			if color_input.lower() == 'cancel':
				print("Edit cancelled")
				return False
			
			# Try as number
			try:
				color_index = int(color_input) - 1
				if 0 <= color_index < len(VALID_COLORS):
					color = VALID_COLORS[color_index]
					continue
			except ValueError:
				pass
			
			valid, msg = EventValidator.validate_color(color_input)
			if valid:
				color = color_input.upper()
			else:
				print(f"   ❌ {msg}")
		
		# Time Window (optional)
		print(f"\n🕐 Time Window (optional)")
		
		# Check if event currently has a time window
		has_time_window = len(old_event) > 6
		
		if has_time_window:
			current_start = old_event[5]
			current_end = old_event[6]
			print(f"   Current: {current_start}:00 - {current_end}:00")
			print(f"\n   Options:")
			print(f"   1. Keep current time window")
			print(f"   2. Change to all-day event")
			print(f"   3. Modify time window")
			
			time_choice = input("\n   Choose (1-3, default=1): ").strip() or "1"
			
			if time_choice == "1":
				# Keep existing
				start_hour = current_start
				end_hour = current_end
			elif time_choice == "2":
				# Remove time window
				start_hour = None
				end_hour = None
				print("   ✓ Changed to all-day event")
			elif time_choice == "3":
				# Modify time window
				start_hour = None
				end_hour = None
				
				while start_hour is None:
					start_input = input(f"   Start hour (0-23) [{current_start}]: ").strip() or current_start
					if start_input.lower() == 'cancel':
						# Keep original
						start_hour = current_start
						end_hour = current_end
						print("   Keeping original time window")
						break
					valid, msg = EventValidator.validate_time(start_input, "Start hour")
					if valid:
						start_hour = start_input
					else:
						print(f"   ❌ {msg}")
				
				# Only ask for end hour if start hour was set/changed
				if start_hour is not None and start_hour != current_start:
					while end_hour is None:
						end_input = input(f"   End hour ({int(start_hour)+1}-23) [{current_end}]: ").strip() or current_end
						if end_input.lower() == 'cancel':
							start_hour = current_start
							end_hour = current_end
							print("   Keeping original time window")
							break
						valid, msg = EventValidator.validate_time(end_input, "End hour")
						if valid:
							if int(end_input) <= int(start_hour):
								print("   ❌ End hour must be after start hour")
								continue
							end_hour = end_input
						else:
							print(f"   ❌ {msg}")
				elif start_hour == current_start:
					# Start hour unchanged, ask if they want to change end
					while end_hour is None:
						end_input = input(f"   End hour ({int(start_hour)+1}-23) [{current_end}]: ").strip() or current_end
						if end_input.lower() == 'cancel':
							end_hour = current_end
							break
						valid, msg = EventValidator.validate_time(end_input, "End hour")
						if valid:
							if int(end_input) <= int(start_hour):
								print("   ❌ End hour must be after start hour")
								continue
							end_hour = end_input
						else:
							print(f"   ❌ {msg}")
			else:
				# Invalid choice, keep original
				print("   Invalid choice - keeping current time window")
				start_hour = current_start
				end_hour = current_end
		else:
			# No existing time window
			print(f"   Current: all-day event")
			
			time_input = input("\n   Add time window? (y/n, default=n): ").strip().lower()
			
			start_hour = None
			end_hour = None
			
			if time_input == 'y':
				# Get start hour
				while start_hour is None:
					start_input = input("   Start hour (0-23, e.g., 8 for 8am): ").strip()
					if start_input.lower() == 'cancel' or not start_input:
						print("   Keeping as all-day event")
						break
					valid, msg = EventValidator.validate_time(start_input, "Start hour")
					if valid:
						start_hour = start_input
					else:
						print(f"   ❌ {msg}")
				
				# Get end hour (only if start was set)
				if start_hour is not None:
					while end_hour is None:
						end_input = input(f"   End hour ({int(start_hour)+1}-23, e.g., 20 for 8pm): ").strip()
						if end_input.lower() == 'cancel' or not end_input:
							start_hour = None  # Reset if cancelled
							print("   Keeping as all-day event")
							break
						valid, msg = EventValidator.validate_time(end_input, "End hour")
						if valid:
							end_val = int(end_input)
							if end_val <= int(start_hour):
								print("   ❌ End hour must be after start hour")
								continue
							end_hour = end_input
						else:
							print(f"   ❌ {msg}")
		
		# Update event
		new_event = [date, top_line, bottom_line, image, color]
		if start_hour is not None and end_hour is not None:
			new_event.append(str(start_hour))
			new_event.append(str(end_hour))
			time_info = f" ({start_hour}:00-{end_hour}:00)"
		else:
			time_info = " (all day)"
		
		self.events[index] = new_event
		print(f"\n✓ Event updated: {date} - {top_line} / {bottom_line}{time_info}")
		return True


def show_available_images():
	"""Display all available images"""
	images = EventValidator.get_available_images()
	
	if not images:
		print(f"\n⚠️  No images found in: {IMAGES_FOLDER}")
		print("Update IMAGES_FOLDER in the script to point to your images/events folder")
		return
	
	print(f"\n🖼️  Available Images ({len(images)} files):")
	print("-" * 60)
	for i, img in enumerate(images, 1):
		print(f"{i:3d}. {img}")
	print("-" * 60)


def interactive_mode():
	"""Interactive menu for managing events"""
	
	# Check images folder on startup
	if not IMAGES_FOLDER.exists():
		print("\n" + "="*80)
		print("⚠️  SETUP REQUIRED")
		print("="*80)
		print(f"Images folder not found: {IMAGES_FOLDER}")
		print("\nEdit this script and update IMAGES_FOLDER to point to:")
		print("  your-pantallita-folder/images/events/")
		print("\nExample:")
		print('  IMAGES_FOLDER = Path.home() / "Documents" / "pantallita" / "images" / "events"')
		print("="*80)
		input("\nPress Enter to continue anyway...")
	
	# Auto-pull latest changes from GitHub on startup
	print("\n📥 Checking for updates from GitHub...")
	try:
		# Configure pull strategy if needed
		config_check = subprocess.run(
			['git', 'config', 'pull.rebase'],
			capture_output=True,
			text=True,
			timeout=5
		)
		
		if config_check.returncode != 0:
			subprocess.run(
				['git', 'config', 'pull.rebase', 'false'],
				capture_output=True,
				timeout=5
			)
		
		# Pull with merge strategy
		result = subprocess.run(
			['git', 'pull', '--no-rebase'],
			capture_output=True,
			text=True,
			timeout=10
		)
		
		if result.returncode == 0:
			if "Already up to date" in result.stdout:
				print("✓ Already up to date")
			else:
				print("✓ Pulled latest changes from GitHub")
				print(f"  {result.stdout.strip()}")
		else:
			if "CONFLICT" in result.stdout or "CONFLICT" in result.stderr:
				print("⚠️  Merge conflict - please resolve manually")
			else:
				print("⚠️  Could not pull from GitHub (using local version)")
	except subprocess.TimeoutExpired:
		print("⚠️  Git pull timeout (using local version)")
	except Exception as e:
		print(f"⚠️  Git pull error: {e} (using local version)")
	
	# CRITICAL: Create manager BEFORE while loop
	manager = EventManager()
	
	while True:
		print("\n" + "="*80)
		print("🎨 PANTALLITA EVENT MANAGER")
		print("="*80)
		print("1. Pull latest from GitHub")
		print("2. List all events")
		print("3. Add new event")
		print("4. Edit event")              # ← NEW
		print("5. Remove event")             # ← Was 4
		print("6. Show available images")    # ← Was 5
		print("7. Validate all events")      # ← Was 6
		print("8. Clean up past events")     # ← Was 7
		print("9. Save changes (local only)") # ← Was 8
		print("10. Review and push to GitHub") # ← Was 9
		print("0. Exit without saving")
		print()
		
		choice = input("Choose an option (0-10): ").strip()  # ← Change to 0-10
		
		if choice == "1":
			# Pull from GitHub
			if manager.git_pull():
				print("\n✓ Reloading events from updated file...")
				manager = EventManager()  # Reload from disk
			else:
				print("\n❌ Pull failed - continuing with current data")
		
		elif choice == "2":
			# List events
			manager.list_events()
		
		elif choice == "3":
			print("\n➕ Add New Event")
			print("(Type 'cancel' at any prompt to return to menu)\n")
			
			# Date
			date = None
			while date is None:
				date_input = input("Date (YYYY-MM-DD): ").strip()
				if date_input.lower() == 'cancel':
					break
				valid, msg = EventValidator.validate_date(date_input)
				if valid:
					date = date_input
				else:
					print(f"   ❌ {msg}")
			
			if not date:
				continue
			
			# Top Line
			print("\n💡 Top Line = displays on TOP of screen")
			top_line = None
			while top_line is None:
				line_input = input("Top Line (max 12 chars): ").strip()
				if line_input.lower() == 'cancel':
					break
				valid, msg = EventValidator.validate_text(line_input, "Top Line", max_length=12)
				if valid:
					top_line = line_input
				else:
					print(f"   ❌ {msg}")
			
			if not top_line:
				continue
			
			# Bottom Line
			print("\n💡 Bottom Line = displays on BOTTOM (usually the name)")
			bottom_line = None
			while bottom_line is None:
				line_input = input("Bottom Line (max 12 chars): ").strip()
				if line_input.lower() == 'cancel':
					break
				valid, msg = EventValidator.validate_text(line_input, "Bottom Line", max_length=12)
				if valid:
					bottom_line = line_input
				else:
					print(f"   ❌ {msg}")
			
			if not bottom_line:
				continue
			
			# Image
			images = EventValidator.get_available_images()
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
					break
				
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
				
				# Validate
				valid, msg = EventValidator.validate_image(img_input)
				if valid:
					image = img_input
				else:
					print(f"   ❌ {msg}")
			
			if not image:
				continue
			
			# Color
			print(f"\n🎨 Available colors:")
			for i, c in enumerate(VALID_COLORS, 1):
				print(f"  {i:2d}. {c}")
			print("\nType number or color name:")
			
			color = None
			while color is None:
				color_input = input("Color (default: 1=MINT): ").strip() or "1"
				
				if color_input.lower() == 'cancel':
					break
				
				# Try as number first
				try:
					color_index = int(color_input) - 1
					if 0 <= color_index < len(VALID_COLORS):
						color = VALID_COLORS[color_index]
						continue
				except ValueError:
					pass
				
				# Try as color name
				valid, msg = EventValidator.validate_color(color_input)
				if valid:
					color = color_input.upper()
				else:
					print(f"   ❌ {msg}")
					print(f"   Enter a number (1-{len(VALID_COLORS)}) or color name")
			
			if not color:
				continue
			
			# Time Window (optional)
			print(f"\n🕐 Time Window (optional)")
			print("   Leave blank for all-day event")
			print("   Or enter hours (0-23) for specific time window")
			
			start_hour = None
			end_hour = None
			
			time_input = input("\nAdd time window? (y/n, default=n): ").strip().lower()
			
			if time_input == 'y':
				# Start hour
				while start_hour is None:
					start_input = input("Start hour (0-23, e.g., 8 for 8am): ").strip()
					if start_input.lower() == 'cancel' or not start_input:
						break
					valid, msg = EventValidator.validate_time(start_input, "Start hour")
					if valid:
						start_hour = int(start_input)
					else:
						print(f"   ❌ {msg}")
				
				# End hour (only if start was set)
				if start_hour is not None:
					while end_hour is None:
						end_input = input(f"End hour ({start_hour+1}-23, e.g., 20 for 8pm): ").strip()
						if end_input.lower() == 'cancel' or not end_input:
							start_hour = None  # Reset if cancelled
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
		
		elif choice == "4":
			# NEW: Edit event
			manager.list_events()
			if not manager.events:
				print("❌ No events to edit")
				continue
			
			try:
				index = int(input("\nEnter event number to edit: "))
				if 0 <= index < len(manager.events):
					manager.edit_event(index)
				else:
					print("❌ Invalid event number")
			except ValueError:
				print("❌ Invalid number")
		
		elif choice == "5":
			manager.list_events()
			try:
				index = int(input("Enter event number to remove: "))
				manager.remove_event(index)
			except ValueError:
				print("❌ Invalid number")
		
		elif choice == "6":
			show_available_images()
		
		elif choice == "7":
			manager.validate_all()
		
		elif choice == "8":
			if manager.cleanup_past_events():
				print("Run option 8 or 9 to save changes")
		
		elif choice == "9":
			manager.save()
			print("\n✓ Changes saved locally")
			print("💡 Run option 10 to push to GitHub")
		
		elif choice == "10":
			# Review before pushing
			if not manager.events:
				print("❌ No events to push")
				continue
			
			if not manager.validate_all():
				print("\n❌ Fix validation errors before pushing")
				continue
			
			# Show review
			if manager.review_and_edit():
				# User approved, save and push
				manager.save()
				if manager.git_push():
					print("\n✅ All done! Events are live on GitHub")
					break
			else:
				print("\n↩️  Push cancelled - returning to main menu")
		
		elif choice == "0":
			confirm = input("Exit without saving? (y/n): ").strip().lower()
			if confirm == 'y':
				print("Exiting without saving.")
				break
		
		else:
			print("❌ Invalid choice")


if __name__ == "__main__":
	interactive_mode()