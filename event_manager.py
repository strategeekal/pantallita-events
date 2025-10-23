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
	
	@classmethod
	def validate_event(cls, date, line1, line2, image, color):
		"""Validate complete event"""
		errors = []
		
		# Validate each field
		valid, msg = cls.validate_date(date)
		if not valid:
			errors.append(f"Date: {msg}")
		
		valid, msg = cls.validate_text(line1, "Line 1", max_length=12)
		if not valid:
			errors.append(msg)
		
		valid, msg = cls.validate_text(line2, "Line 2", max_length=12)
		if not valid:
			errors.append(msg)
		
		valid, msg = cls.validate_image(image)
		if not valid:
			errors.append(msg)
		
		valid, msg = cls.validate_color(color)
		if not valid:
			errors.append(msg)
		
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
	
	def add_event(self, date, line1, line2, image, color="MINT"):
		"""Add a new event with validation"""
		# Validate
		valid, errors = EventValidator.validate_event(date, line1, line2, image, color)
		
		if not valid:
			print("❌ Validation failed:")
			for error in errors:
				print(f"   - {error}")
			return False
		
		# Add event
		event = [date, line1, line2, image, color.upper()]
		self.events.append(event)
		print(f"✓ Added: {date} - {line1} {line2}")
		return True
	
	def remove_event(self, index):
		"""Remove event by index"""
		if 0 <= index < len(self.events):
			removed = self.events.pop(index)
			print(f"✓ Removed: {removed[0]} - {removed[1]} {removed[2]}")
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
		print("=" * 80)
		
		if future_events:
			print("\n🔮 FUTURE EVENTS (will be imported):")
			print("-" * 80)
			for i, event in future_events:
				date, line1, line2, image, color = event
				print(f"{i:2d}. {date} | {line1:12s} {line2:12s} | {image:20s} | {color}")
		
		if past_events:
			print("\n📜 PAST EVENTS (will be skipped):")
			print("-" * 80)
			for i, event in past_events:
				date, line1, line2, image, color = event
				print(f"{i:2d}. {date} | {line1:12s} {line2:12s} | {image:20s} | {color}")
		
		print("=" * 80)
		print(f"Total: {len(self.events)} events ({len(future_events)} future, {len(past_events)} past)\n")
	
	def save(self):
		"""Save events to CSV"""
		# Sort events by date
		self.events.sort(key=lambda x: x[0])
		
		with open(self.filename, 'w', newline='') as f:
			writer = csv.writer(f)
			
			# Write header comment
			writer.writerow(['# Ephemeral Events - Auto-generated'])
			writer.writerow(['# Date,Line1,Line2,Image,Color'])
			
			# Write events
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
			
			date, line1, line2, image, color = event[:5]
			valid, errors = EventValidator.validate_event(date, line1, line2, image, color)
			
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
			result = subprocess.run(['git', 'pull'], capture_output=True, text=True, cwd='.')
			
			if result.returncode == 0:
				print("✓ Successfully pulled from GitHub!")
				if "Already up to date" in result.stdout:
					print("  (No changes - already up to date)")
				else:
					print(f"  {result.stdout.strip()}")
				return True
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
		
		print("\n" + "="*80)
		print("📋 REVIEW EVENTS BEFORE PUSHING")
		print("="*80)
		
		if future_events:
			print(f"\n✅ FUTURE EVENTS ({len(future_events)} will be imported by Pantallita):")
			print("-" * 80)
			for i, event in future_events:
				date, line1, line2, image, color = event
				print(f"{i:2d}. {date} | {line1:12s} {line2:12s} | {image:20s} | {color}")
		
		if past_events:
			print(f"\n⏳ PAST EVENTS ({len(past_events)} will be skipped by Pantallita):")
			print("-" * 80)
			for i, event in past_events:
				date, line1, line2, image, color = event
				print(f"{i:2d}. {date} | {line1:12s} {line2:12s} | {image:20s} | {color}")
		
		print("="*80)
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
		print(f"\n✏️  Editing event: {old_event[0]} - {old_event[1]} {old_event[2]}")
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
		
		# Line 1
		line1 = None
		while line1 is None:
			current = old_event[1]
			line1_input = input(f"Line 1 [{current}]: ").strip() or current
			if line1_input.lower() == 'cancel':
				print("Edit cancelled")
				return False
			valid, msg = EventValidator.validate_text(line1_input, "Line 1", max_length=12)
			if valid:
				line1 = line1_input
			else:
				print(f"   ❌ {msg}")
		
		# Line 2
		line2 = None
		while line2 is None:
			current = old_event[2]
			line2_input = input(f"Line 2 [{current}]: ").strip() or current
			if line2_input.lower() == 'cancel':
				print("Edit cancelled")
				return False
			valid, msg = EventValidator.validate_text(line2_input, "Line 2", max_length=12)
			if valid:
				line2 = line2_input
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
			current = old_event[4]
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
		
		# Update event
		self.events[index] = [date, line1, line2, image, color]
		print(f"\n✓ Event updated: {date} - {line1} {line2}")
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
		result = subprocess.run(['git', 'pull'], capture_output=True, text=True, timeout=10)
		if result.returncode == 0:
			if "Already up to date" in result.stdout:
				print("✓ Already up to date")
			else:
				print("✓ Pulled latest changes from GitHub")
				print(f"  {result.stdout.strip()}")
		else:
			print("⚠️  Could not pull from GitHub (using local version)")
	except subprocess.TimeoutExpired:
		print("⚠️  Git pull timeout (using local version)")
	except Exception as e:
		print(f"⚠️  Git pull error: {e} (using local version)")
	
	# CRITICAL: Create manager BEFORE while loop
	manager = EventManager()  # ← Make sure this line is HERE, before while loop
	
	while True:
		print("\n" + "="*80)
		print("🎨 PANTALLITA EVENT MANAGER")
		print("="*80)
		print("1. Pull latest from GitHub")
		print("2. List all events")
		print("3. Add new event")
		print("4. Remove event")
		print("5. Show available images")
		print("6. Validate all events")
		print("7. Clean up past events")
		print("8. Save changes (local only)")
		print("9. Review and push to GitHub")
		print("0. Exit without saving")
		print()
		
		choice = input("Choose an option (0-9): ").strip()
		
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
			
			# Line 1
			line1 = None
			while line1 is None:
				line1_input = input("Line 1 (max 12 chars): ").strip()
				if line1_input.lower() == 'cancel':
					break
				valid, msg = EventValidator.validate_text(line1_input, "Line 1", max_length=12)
				if valid:
					line1 = line1_input
				else:
					print(f"   ❌ {msg}")
			
			if not line1:
				continue
			
			# Line 2
			line2 = None
			while line2 is None:
				line2_input = input("Line 2 (max 12 chars): ").strip()
				if line2_input.lower() == 'cancel':
					break
				valid, msg = EventValidator.validate_text(line2_input, "Line 2", max_length=12)
				if valid:
					line2 = line2_input
				else:
					print(f"   ❌ {msg}")
			
			if not line2:
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
			
			# Add event (should always succeed)
			manager.add_event(date, line1, line2, image, color)
		
		elif choice == "4":
			manager.list_events()
			try:
				index = int(input("Enter event number to remove: "))
				manager.remove_event(index)
			except ValueError:
				print("❌ Invalid number")
		
		elif choice == "5":
			show_available_images()
		
		elif choice == "6":
			manager.validate_all()
		
		elif choice == "7":
			if manager.cleanup_past_events():
				print("Run option 7 or 8 to save changes")
		
		elif choice == "8":
			manager.save()
			print("\n✓ Changes saved locally")
			print("💡 Run option 8 to push to GitHub")
		
		elif choice == "9":
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