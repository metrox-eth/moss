# The same environment as ../mujoco (MuJoCo 3.3.7, NumPy):
#     python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt
PYTHON ?= .venv/bin/python

.PHONY: all budget cycle servos tipping spring pick report

all: budget cycle servos tipping spring pick report

budget:   ; $(PYTHON) -m s1_torque_budget
cycle:    ; $(PYTHON) -m s2_cycle
servos:   ; $(PYTHON) -m s3_two_servos
tipping:  ; $(PYTHON) -m s4_tipping
spring:   ; $(PYTHON) -m s5_spring
pick:     ; $(PYTHON) -m s6_pick_point
report:   ; $(PYTHON) -m report
