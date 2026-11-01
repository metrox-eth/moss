// SPDX-License-Identifier: Apache-2.0
#pragma once
#include <stdint.h>
#include <stddef.h>
#define ESP_OK 0
#define UART_NUM_1 1
#define UART_DATA_8_BITS 8
#define UART_PARITY_DISABLE 0
#define UART_STOP_BITS_1 1
#define UART_HW_FLOWCTRL_DISABLE 0
#define UART_SCLK_DEFAULT 0
#define UART_PIN_NO_CHANGE -1
struct uart_config_t{int baud_rate,data_bits,parity,stop_bits,flow_ctrl,source_clk;};
int uart_param_config(int,const uart_config_t*);
int uart_set_pin(int,int,int,int,int);
int uart_driver_install(int,int,int,int,void*,int);
int uart_flush_input(int);
int uart_wait_tx_done(int,int);
int uart_tx_chars(int,const char*,uint32_t);
int uart_read_bytes(int,uint8_t*,int,int);
