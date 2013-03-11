# loopcounter.py Alan Si (asi@uwo.ca)
# this program determines how many time the Research-o-Matic Nozzle will repeat its spray pattern
# input values are in mm, mm, mm, cm/s, and ML/hr respectively

def pattern_loops(x, y, spacing, feedrate, flowrate, volume):
  n = (y / spacing) + 1
  pause = 0.6 # This needs to change
  print_time = ((n * x) + y + (pause * ((2 * n) - 2))) / feedrate
  down_time = 2.0 # This needs to change

  cycle_time = down_time + print_time
  syringe_time = volume / flowrate

  print ("Pause and Downtime and feedrate/flowrate conversion needs to be done")

  return ((syringe_time // cycle_time) + 1)