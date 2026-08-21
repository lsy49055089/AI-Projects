#include "stm32f4xx.h"
#include "option.h"
#include "macro.h"
#include "malloc.h"

// Uart.c

extern void Uart2_Init(int baud);
extern void Uart2_Send_Byte(char data);
extern void Uart2_RX_Interrupt_Enable(int en);

extern void Uart1_Init(int baud);
extern void Uart1_Send_Byte(char data);
extern void Uart1_Send_String(char *pt);
extern void Uart1_Printf(char *fmt,...);
extern char Uart1_Get_Char(void);
extern char Uart1_Get_Pressed(void);

// SysTick.c

extern void SysTick_Run(unsigned int msec);
extern int SysTick_Check_Timeout(void);
extern unsigned int SysTick_Get_Time(void);
extern unsigned int SysTick_Get_Load_Time(void);
extern void SysTick_Stop(void);

// Led.c

extern void LED_Init(void);
extern void LED_On(unsigned int led);
extern void LED_Off(unsigned int led);
extern void LED_Display(unsigned int data);

// Clock.c

extern void Clock_Init(void);

// Key.c

#define BTN_NONE   0
#define BTN1       1
#define BTN2       2
#define BTN3       3
#define BTN_MULTI  4


/*
 * 실제 버튼의 물리적 위치
 *
 * 기존 회로에서 BTN 번호와 물리 위치가 반대임
 */
#define BUTTON_LEFT      BTN1
#define BUTTON_MIDDLE    BTN2
#define BUTTON_RIGHT     BTN3




extern void Button_Init(void);
extern int Button_Get_Raw(void);
extern int Button_Confirm_Pressed(int button);
extern void Button_Wait_All_Released(void);

extern void Key_Poll_Init(void);
extern int Key_Get_Pressed(void);
extern void Key_Wait_Key_Released(void);
extern void Key_Wait_Key_Pressed(void);
extern void Key_ISR_Enable(int en);

// Timer.c

extern void TIM2_Delay(int time);
extern void TIM2_Stopwatch_Start(void);
extern unsigned int TIM2_Stopwatch_Stop(void);
extern unsigned int TIM2_Stopwatch_Get_Time(void);
extern void TIM4_Repeat(int time);
extern int TIM4_Check_Timeout(void);
extern void TIM4_Stop(void);
extern void TIM4_Change_Value(int time);
extern void TIM4_Repeat_Interrupt_Enable(int en, int time);
extern void TIM3_Out_Init(void);
extern void TIM3_Out_Freq_Generation(unsigned short freq);
extern void TIM3_Out_Stop(void);

// i2c.c

#define SC16IS752_IODIR				0x0A
#define SC16IS752_IOSTATE			0x0B

extern void I2C1_SC16IS752_Init(unsigned int freq);
extern void I2C1_SC16IS752_Write_Reg(unsigned int addr, unsigned int data);
extern void I2C1_SC16IS752_Config_GPIO(unsigned int config);
extern void I2C1_SC16IS752_Write_GPIO(unsigned int data);

// spi.c

extern void SPI1_SC16IS752_Init(unsigned int div);
extern void SPI1_SC16IS752_Write_Reg(unsigned int addr, unsigned int data);
extern void SPI1_SC16IS752_Config_GPIO(unsigned int config);
extern void SPI1_SC16IS752_Write_GPIO(unsigned int data);

// Adc.c

extern void ADC1_IN6_Init(void);
extern void ADC1_Start(void);
extern void ADC1_Stop(void);
extern int ADC1_Get_Status(void);
extern int ADC1_Get_Data(void);

// lcd.c

extern void LCD_Init(void);
extern int LCD_Is_Ready(void);

extern void LCD_Clear(void);
extern void LCD_Home(void);

extern void LCD_Set_Cursor(unsigned int row,
                           unsigned int col);

extern void LCD_Write_Char(char data);
extern void LCD_Print(const char *string);

extern void LCD_Print_Line(unsigned int row,
                           const char *string);

extern void LCD_Backlight_On(void);
extern void LCD_Backlight_Off(void);



// game_lcd.c

extern void Game_LCD_Show_Start(void);

extern void Game_LCD_Show_Wait(unsigned int round,
                               unsigned int total_round,
                               unsigned int limit_ms);

extern void Game_LCD_Show_Go(unsigned int target_led,
                             unsigned int target_button);

extern void Game_LCD_Show_Correct(unsigned int reaction_ms);

extern void Game_LCD_Show_Wrong(unsigned int pressed_button,
                                unsigned int correct_button);

extern void Game_LCD_Show_Timeout(unsigned int limit_ms);

extern void Game_LCD_Show_Early(void);

extern void Game_LCD_Show_Clear(unsigned int average_ms);

extern void Game_LCD_Show_Game_Over(unsigned int round);


// buzzer.c
extern void Buzzer_Init(void);

extern void Buzzer_On(void);
extern void Buzzer_Off(void);

extern void Buzzer_Correct(void);
extern void Buzzer_Wrong(void);
extern void Buzzer_Timeout(void);
extern void Buzzer_Clear(void);

extern void Buzzer_Select_Reaction(void);
extern void Buzzer_Select_Memory(void);

extern void Buzzer_Start_Reaction(void);
extern void Buzzer_Start_Memory(void);

/*
 * Joystick direction
 */
#define JOY_NONE       0
#define JOY_UP         1
#define JOY_DOWN       2
#define JOY_LEFT       3
#define JOY_RIGHT      4


/*
 * joystick.c
 */
extern void Joystick_Init(void);

extern unsigned int Joystick_Read_X(void);
extern unsigned int Joystick_Read_Y(void);

extern int Joystick_SW_Is_Pressed(void);

extern int Joystick_Get_Direction(void);
extern int Joystick_Wait_Direction(void);

extern void Joystick_Wait_Center(void);
extern void Joystick_Calibrate_Center(void);


/*
 * memory_game.c
 */
extern void Run_Memory_Game(void);