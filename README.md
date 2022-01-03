# PyCTA
A Python wrapper for interacting with the CTA Transit Feeds:  

- **BusTrackerAPI**  
- **TrainTrackerAPI**  
- **CustomerAlertsAPI**
<br>

## Quick Start
```python
import cta

# API Wrappers
bt = cta.BusTracker()
tt = cta.TrainTracker()
```

## Stop Search / Reference
```python
ss = cta.StopSearch()

# Search for stops with "fullerton" in stop name
ss.find_stop('fullerton')

# Same search but only return train stops (stations)
ss.find_stop('fullerton',stop_type='train')

# Search for the bus stop at the intersection of Clark & Diversey
ss.find_stop('clark and diversey',stop_type='bus')
```

## Bus Tracking
```python
# Arrival Predictions by stop ID

bt.predictions(stpid="1836")

# Arrival Predictions for a single vehicle (vehicle ID).

bt.predictions(stpid="1836")
```
