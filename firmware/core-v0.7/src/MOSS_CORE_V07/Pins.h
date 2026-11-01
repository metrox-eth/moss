// SPDX-License-Identifier: Apache-2.0
#pragma once
namespace pins {
constexpr int ESTOP_ACTIVE = 4, ENC_R_A = 5, ENC_L_B = 6, ENC_L_A = 7,
              STATUS_LED = 15;
constexpr int ENC_R_B = 16, DIR_L = 17, PWM_L = 18, DIR_R = 8, PWM_R = 9;
constexpr int AUDIO_BCLK = 10, AUDIO_LRCLK = 11, AUDIO_DATA = 12,
              AUDIO_ENABLE = 13;
constexpr int USB_PWR_FAULT_N = 14, DRIVE_ENABLE = 21, WD_ENABLE = 47,
              WD_TICK = 48;
constexpr int SERVO_TX = 35, SERVO_TX_ENABLE = 36, SERVO_RX = 37;
constexpr int ACT_POWER_ENABLE = 38, ACT_READY = 39, I2C_SCL = 40, I2C_SDA = 41;
constexpr int ENC_POWER_EN = 42, DRIVE_RUN = 44, DEBUG_TX = 43, ARM_LATCHED = 2,
              ARM_COMMIT = 1;
constexpr int ESP_USB_N = 19, ESP_USB_P = 20, BOOT_N = 0;
} // namespace pins
