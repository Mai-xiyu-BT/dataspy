# 🔍 DataSpy

Monitor any website, API, or data source for changes. Get notified instantly.

## Features

- 🌐 **Universal Monitoring** - Any URL, API endpoint, or web page
- ⚡ **Real-time Alerts** - Instant notifications on changes
- 📊 **History Tracking** - Full change history with diffs
- 🔄 **Flexible Scheduling** - From seconds to days
- 💾 **Local Storage** - Your data stays on your machine

## Installation

```bash
git clone https://github.com/yourusername/dataspy
cd dataspy
chmod +x dataspy
```

## Quick Start

```bash
# Add a monitoring task
./dataspy add --id hn_top --name "Hacker News" --url "https://news.ycombinator.com" --interval 3600

# List all tasks
./dataspy list

# Check now
./dataspy check hn_top

# Start monitoring daemon
./dataspy monitor
```

## Use Cases

### Price Monitoring
Track product prices and get notified of drops:
```bash
./dataspy add --id amazon_product --name "Product Price" \
  --url "https://amazon.com/product" --interval 7200
```

### Competitor Tracking
Monitor competitor websites for changes:
```bash
./dataspy add --id competitor --name "Competitor Site" \
  --url "https://competitor.com/pricing" --interval 86400
```

### API Health Check
Ensure your APIs are responding correctly:
```bash
./dataspy add --id my_api --name "API Status" \
  --url "https://api.example.com/health" --interval 300
```

### Content Updates
Track blog posts, news, or documentation:
```bash
./dataspy add --id blog --name "Tech Blog" \
  --url "https://blog.example.com" --interval 3600
```

## Commands

| Command | Description |
|---------|-------------|
| `add` | Add new monitoring task |
| `list` | List all tasks |
| `check` | Check a task immediately |
| `remove` | Remove a task |
| `events` | View change history |
| `monitor` | Start monitoring daemon |

## Pricing

- **Free**: 5 monitors, hourly checks
- **Pro** ¥9.9/month: 20 monitors, 15-min checks, email alerts
- **Enterprise** ¥39/month: Unlimited, real-time, API access

## Business Model

DataSpy can be monetized as:
1. **Self-hosted tool** - Open source, donations
2. **SaaS service** - Hosted version with subscription
3. **API service** - Pay-per-check model
4. **White-label** - License to businesses

## Tech Stack

- Python 3.8+
- SQLite (local storage)
- Requests (HTTP)
- Optional: Playwright (browser rendering)

## License - Dual Licensing

### Open Source (MIT)
Free for personal, educational, and open-source projects. Must include attribution.

See [LICENSE-MIT](LICENSE-MIT) for details.

### Commercial License
For businesses wanting to:
- Use in proprietary products
- Remove attribution
- Get dedicated support

**Pricing:**
- Startup (<$1M): $99/year per project
- Business ($1M-$10M): $499/year per project
- Enterprise (>$10M): $1,999/year per project
- Unlimited: $4,999/year all projects

**Contact:** Open a GitHub issue for commercial licensing.

### You Are Buying From the Original Author (原厂)
All rights reserved by the original developers.
