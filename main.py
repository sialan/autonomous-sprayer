import gcode, dxf, loopcounter
import time
import sys

go_again = "Y"

while go_again == "Y" or "y":
  pattern = raw_input("Please enter the spray pattern desired: ")
  xwidth = input("Please enter the width of the sample (x-direction) in mm: ")
  ylength = input("Please enter the length of the sample (y-direction)in mm: ")
  spacing = input("Please enter the spacing between spray passes: ")
  feedrate = input("Please enter the speed of the sample plate in mm/s: ") ####NEed conversions within program
  flowrate = input("Please enter the flowrate of the syringe spray passes: ") ###also need conversions
  volume = input("Please enter the total volume of Solution: ") # CONVERSIONS BATMAN!

  dxf_file = dxf.dxf_render(pattern, xwidth, ylength, spacing)
  number_of_repeats = loopcounter.pattern_loops(xwidth, ylength, spacing, feedrate, flowrate, volume)
  print number_of_repeats
  """
  repeat_pattern = loopcounter.patternloops(xwidth, ylength, spacing, feedrate, flowrate)
  gcode_file = gcode.gcode_render()
  ppl_file = ppl.ppl_render()
  """
  #Launch pump and ReplicatorG programs
  """
  as;flksjdflsdjf
  """

  go_again = raw_input("Would you like to spray another sample? (Y/N): ")
  if go_again != "Y" or "y" or "N" or "n":
    print("Invalid input. If you wish to spray another sample please restart the program")

  #delete files
  print("delete")

  
time.sleep(5)