# Pantallita Events
**Version 1.0.0**

A file and image repository used by RGB matrix displays to gather changing event and daily schedule information remotely
```

## CSV File Formats

### Events CSV (`ephemeral_events.csv`)

**Format:**
```
YYYY-MM-DD,TopLine,BottomLine,Image,Color[,StartHour,EndHour]
```

**Fields:**
- `YYYY-MM-DD` - Event date (ISO format)
- `TopLine` - Top line text (max 12 chars)
- `BottomLine` - Bottom line text (max 12 chars)
- `Image` - BMP image filename from `img/events/` (e.g., `halloween.bmp`)
- `Color` - Color name: `MINT`, `LILAC`, `ORANGE`, `YELLOW`, `BLUE`, `WHITE`, `RED`, `GREEN`, `PINK`, `PURPLE`
- `StartHour` - Optional, hour when event becomes active (0-23)
- `EndHour` - Optional, hour when event ends (0-23)

**Example:**
```csv
2025-12-25,Merry,Christmas,tree.bmp,GREEN,0,23
2025-01-01,Happy,New Year,fireworks.bmp,YELLOW,0,12
```

### Schedules CSV (`default_schedule.csv` or `schedule_YYYY-MM-DD.csv`)

**Format:**
```
name,enabled,days,start_hour,start_min,end_hour,end_min,image,progressbar
```

**Fields:**
- `name` - Schedule item name/description
- `enabled` - `1` = enabled, `0` = disabled
- `days` - Day numbers for default schedules: `0-6` = Mon-Sun (e.g., `01234` = Mon-Fri, `56` = Sat-Sun)
  - For date-specific schedules, use empty string or `0123456`
- `start_hour` - Start hour (0-23)
- `start_min` - Start minute (0-59)
- `end_hour` - End hour (0-23)
- `end_min` - End minute (0-59)
- `image` - BMP image filename from `img/schedules/` (e.g., `go_to_school.bmp`)
- `progressbar` - `1` = show progress bar, `0` = hide

**Example:**
```csv
# default_schedule.csv
Wake Up,1,0123456,7,0,7,30,wake_up.bmp,1
Go to School,1,01234,8,0,15,0,go_to_school.bmp,1
Dinner Time,1,0123456,18,30,19,30,dinner.bmp,0
Bedtime,1,0123456,21,0,21,30,sleep.bmp,1
Weekend Fun,1,56,10,0,12,0,play.bmp,0
```

### Template CSV (`template_NAME.csv`)

Same format as schedule CSV files. Templates are stored in the repository and can be loaded into any schedule.

## GitHub Repository Structure

```
pantallita-events/                # Independent repo with files
├── ephemeral_events.csv          # Events file
├── schedules/
    ├── default_schedule.csv      # Default daily schedule
    ├── schedule_YYYY-MM-DD.csv   # Date-specific schedules
    ├── templates/
        └── NAME.csv              # Schedule templates
└── img/
    ├── events/                   # Event images (27x28 BMP)
    │   ├── halloween.bmp
    │   ├── birthday.bmp
    │   └── ...
    ├── schedules/                # Schedule images (40x28 BMP)
    │   ├── get_dressed.bmp
    │   ├── go_to_school.bmp
    │   └── ...
    └── weather/
        └── columns/              # Weather icons (3x16 BMP)
            └── 1.bmp
