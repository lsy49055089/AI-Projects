#include "device_driver.h"

/*
 * 1602 LCD + PCF8574 I2C Backpack Driver
 *
 * LCD I2C address : 0x3F (7-bit)
 * SCL             : D15 = PB8 = I2C1_SCL
 * SDA             : D14 = PB9 = I2C1_SDA
 *
 * 주의:
 * 현재 게임의 BTN3가 PB6을 사용하므로
 * 기존 i2c.c의 PB6/PB7 설정은 LCD에 사용하지 않는다.
 */

#define LCD_I2C_ADDRESS          0x27u
#define LCD_I2C_SPEED            100000u
#define LCD_I2C_TIMEOUT          1000000u

#define LCD_RS                   0x01u
#define LCD_RW                   0x02u
#define LCD_EN                   0x04u
#define LCD_BACKLIGHT            0x08u

#define LCD_COMMAND_MODE         0x00u
#define LCD_DATA_MODE            LCD_RS

#define LCD_LINE1_ADDRESS        0x00u
#define LCD_LINE2_ADDRESS        0x40u
#define LCD_COLUMN_COUNT         16u

static unsigned int LCD_Ready = 0u;
static unsigned char LCD_Backlight_State = LCD_BACKLIGHT;


/*
 * TIM2와 SysTick을 사용하지 않는 지연 함수
 * LCD 초기화와 Enable 펄스 생성에 사용
 */
static void LCD_Delay_us(unsigned int usec)
{
    unsigned int start;
    unsigned int ticks;

    ticks = (HCLK / 1000000u) * usec;
    start = DWT->CYCCNT;

    while ((unsigned int)(DWT->CYCCNT - start) < ticks)
    {
    }
}


static void LCD_Delay_ms(unsigned int msec)
{
    while (msec > 0u)
    {
        LCD_Delay_us(1000u);
        msec--;
    }
}


/*
 * I2C1 사용 핀 설정
 * PB8 = SCL, PB9 = SDA, AF4
 */
static void LCD_I2C1_Init(void)
{
    unsigned int ccr;

    /* GPIOB, I2C1 Clock Enable */
    Macro_Set_Bit(RCC->AHB1ENR, 1);
    Macro_Set_Bit(RCC->APB1ENR, 21);

    /* I2C1 Peripheral Reset */
    Macro_Set_Bit(RCC->APB1RSTR, 21);
    Macro_Clear_Bit(RCC->APB1RSTR, 21);

    /* PB8, PB9 = Alternate Function */
    Macro_Write_Block(GPIOB->MODER,
                      0xFu,
                      0xAu,
                      8u * 2u);

    /* PB8, PB9 = AF4(I2C1) */
    Macro_Write_Block(GPIOB->AFR[1],
                      0xFFu,
                      0x44u,
                      0u);

    /* Open-Drain */
    Macro_Set_Area(GPIOB->OTYPER,
                   0x3u,
                   8u);

    /* Fast Speed */
    Macro_Write_Block(GPIOB->OSPEEDR,
                      0xFu,
                      0xAu,
                      8u * 2u);

    /* Internal Pull-up */
    Macro_Write_Block(GPIOB->PUPDR,
                      0xFu,
                      0x5u,
                      8u * 2u);

    /* I2C Disable before configuration */
    Macro_Clear_Bit(I2C1->CR1, 0);

    /* APB1 clock frequency in MHz */
    Macro_Write_Block(I2C1->CR2,
                      0x27u,
                      PCLK1 / 1000000u,
                      0u);

    /* Standard Mode: SCL = PCLK1 / (2 * CCR) */
    ccr = PCLK1 / (LCD_I2C_SPEED * 2u);

    if (ccr < 4u)
    {
        ccr = 4u;
    }

    I2C1->CCR = ccr;
    I2C1->TRISE = (PCLK1 / 1000000u) + 1u;

    /* ACK Enable, I2C Enable */
    Macro_Set_Bit(I2C1->CR1, 10);
    Macro_Set_Bit(I2C1->CR1, 0);
}


/*
 * PCF8574로 1바이트 전송
 * 성공: 1, 실패/Timeout: 0
 */
static int LCD_I2C1_Write_Byte(unsigned char data)
{
    unsigned int timeout;
    volatile unsigned int dummy;

    /* BUSY가 풀릴 때까지 대기 */
    timeout = LCD_I2C_TIMEOUT;

    while (Macro_Check_Bit_Set(I2C1->SR2, 1))
    {
        if (--timeout == 0u)
        {
            return 0;
        }
    }

    /* START 생성 */
    Macro_Set_Bit(I2C1->CR1, 8);

    timeout = LCD_I2C_TIMEOUT;

    while (Macro_Check_Bit_Clear(I2C1->SR1, 0))
    {
        if (--timeout == 0u)
        {
            Macro_Set_Bit(I2C1->CR1, 9);
            return 0;
        }
    }

    /* 7-bit 주소를 왼쪽으로 한 칸 이동, Write = 0 */
    I2C1->DR = (LCD_I2C_ADDRESS << 1u);

    timeout = LCD_I2C_TIMEOUT;

    for (;;)
    {
        /* ADDR = 1: Slave ACK 수신 */
        if (Macro_Check_Bit_Set(I2C1->SR1, 1))
        {
            break;
        }

        /* AF = 1: Slave NACK */
        if (Macro_Check_Bit_Set(I2C1->SR1, 10))
        {
            Macro_Clear_Bit(I2C1->SR1, 10);
            Macro_Set_Bit(I2C1->CR1, 9);
            return 0;
        }

        if (--timeout == 0u)
        {
            Macro_Set_Bit(I2C1->CR1, 9);
            return 0;
        }
    }

    /* SR1, SR2 순서로 읽어 ADDR Flag Clear */
    dummy = I2C1->SR1;
    dummy = I2C1->SR2;
    (void)dummy;

    /* TXE 대기 */
    timeout = LCD_I2C_TIMEOUT;

    while (Macro_Check_Bit_Clear(I2C1->SR1, 7))
    {
        if (--timeout == 0u)
        {
            Macro_Set_Bit(I2C1->CR1, 9);
            return 0;
        }
    }

    I2C1->DR = data;

    /* BTF 대기 */
    timeout = LCD_I2C_TIMEOUT;

    while (Macro_Check_Bit_Clear(I2C1->SR1, 2))
    {
        if (--timeout == 0u)
        {
            Macro_Set_Bit(I2C1->CR1, 9);
            return 0;
        }
    }

    /* STOP 생성 */
    Macro_Set_Bit(I2C1->CR1, 9);

    return 1;
}


static int LCD_Expander_Write(unsigned char data)
{
    return LCD_I2C1_Write_Byte(data | LCD_Backlight_State);
}


static void LCD_Pulse_Enable(unsigned char data)
{
    LCD_Expander_Write(data | LCD_EN);
    LCD_Delay_us(2u);

    LCD_Expander_Write(data & (unsigned char)(~LCD_EN));
    LCD_Delay_us(50u);
}


static void LCD_Write_4Bits(unsigned char data)
{
    LCD_Expander_Write(data);
    LCD_Pulse_Enable(data);
}


/*
 * LCD 초기화 초기에 사용하는 4-bit 전송
 * 상위 4비트만 전송한다.
 */
static void LCD_Write_Init_Nibble(unsigned char data)
{
    LCD_Write_4Bits(data & 0xF0u);
}


static void LCD_Send(unsigned char value,
                     unsigned char mode)
{
    unsigned char high_nibble;
    unsigned char low_nibble;

    high_nibble = (value & 0xF0u) | mode;
    low_nibble  = ((value << 4u) & 0xF0u) | mode;

    LCD_Write_4Bits(high_nibble);
    LCD_Write_4Bits(low_nibble);
}


static void LCD_Command(unsigned char command)
{
    if (!LCD_Ready)
    {
        return;
    }

    LCD_Send(command, LCD_COMMAND_MODE);

    /* Clear와 Home 명령은 처리 시간이 길다. */
    if ((command == 0x01u) ||
        (command == 0x02u))
    {
        LCD_Delay_ms(2u);
    }
}


void LCD_Init(void)
{
    /* DWT Cycle Counter Enable */
    CoreDebug->DEMCR |= CoreDebug_DEMCR_TRCENA_Msk;
    DWT->CYCCNT = 0u;
    DWT->CTRL |= DWT_CTRL_CYCCNTENA_Msk;

    LCD_I2C1_Init();

    /* LCD 전원 안정화 대기 */
    LCD_Delay_ms(50u);

    /* LCD 주소 ACK 확인 */
    if (!LCD_I2C1_Write_Byte(LCD_Backlight_State))
    {
        LCD_Ready = 0u;
        return;
    }

    LCD_Ready = 1u;

    /* HD44780 4-bit 초기화 순서 */
    LCD_Write_Init_Nibble(0x30u);
    LCD_Delay_ms(5u);

    LCD_Write_Init_Nibble(0x30u);
    LCD_Delay_us(200u);

    LCD_Write_Init_Nibble(0x30u);
    LCD_Delay_us(200u);

    LCD_Write_Init_Nibble(0x20u);
    LCD_Delay_us(200u);

    /* 4-bit, 2-line, 5x8 font */
    LCD_Command(0x28u);

    /* Display OFF */
    LCD_Command(0x08u);

    /* Display Clear */
    LCD_Command(0x01u);

    /* Entry Mode: cursor moves right */
    LCD_Command(0x06u);

    /* Display ON, Cursor OFF, Blink OFF */
    LCD_Command(0x0Cu);
}


int LCD_Is_Ready(void)
{
    return (int)LCD_Ready;
}


void LCD_Clear(void)
{
    LCD_Command(0x01u);
}


void LCD_Home(void)
{
    LCD_Command(0x02u);
}


void LCD_Set_Cursor(unsigned int row,
                    unsigned int col)
{
    unsigned int address;

    if (!LCD_Ready)
    {
        return;
    }

    if (row > 1u)
    {
        row = 1u;
    }

    if (col >= LCD_COLUMN_COUNT)
    {
        col = LCD_COLUMN_COUNT - 1u;
    }

    if (row == 0u)
    {
        address = LCD_LINE1_ADDRESS + col;
    }
    else
    {
        address = LCD_LINE2_ADDRESS + col;
    }

    LCD_Command((unsigned char)(0x80u | address));
}


void LCD_Write_Char(char data)
{
    if (!LCD_Ready)
    {
        return;
    }

    LCD_Send((unsigned char)data, LCD_DATA_MODE);
}


void LCD_Print(const char *string)
{
    if ((!LCD_Ready) ||
        (string == (const char *)0))
    {
        return;
    }

    while (*string != '\0')
    {
        LCD_Write_Char(*string);
        string++;
    }
}


/*
 * 한 줄을 항상 16칸으로 덮어쓴다.
 * 이전 글자가 화면에 남는 것을 방지한다.
 */
void LCD_Print_Line(unsigned int row,
                    const char *string)
{
    unsigned int col;
    char data;

    if (!LCD_Ready)
    {
        return;
    }

    LCD_Set_Cursor(row, 0u);

    for (col = 0u;
         col < LCD_COLUMN_COUNT;
         col++)
    {
        data = ' ';

        if ((string != (const char *)0) &&
            (*string != '\0'))
        {
            data = *string;
            string++;
        }

        LCD_Write_Char(data);
    }
}


void LCD_Backlight_On(void)
{
    LCD_Backlight_State = LCD_BACKLIGHT;

    if (LCD_Ready)
    {
        LCD_Expander_Write(0u);
    }
}


void LCD_Backlight_Off(void)
{
    LCD_Backlight_State = 0u;

    if (LCD_Ready)
    {
        LCD_Expander_Write(0u);
    }
}