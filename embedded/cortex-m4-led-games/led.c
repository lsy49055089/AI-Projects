#include "device_driver.h"

#define LED_PIN_START    5u
#define LED_COUNT        3u
#define LED_MASK         0x7u

void LED_Init(void)
{
    /* GPIOA Clock Enable */
    Macro_Set_Bit(RCC->AHB1ENR, 0);

    /*
     * PA5, PA6, PA7 출력 모드
     *
     * PA5 MODER = 01
     * PA6 MODER = 01
     * PA7 MODER = 01
     *
     * 01 01 01 = 0x15
     */
    Macro_Write_Block(GPIOA->MODER,
                      0x3Fu,
                      0x15u,
                      LED_PIN_START * 2);

    /* Push-Pull */
    Macro_Clear_Area(GPIOA->OTYPER,
                     LED_MASK,
                     LED_PIN_START);

    /* Pull-up / Pull-down 사용 안 함 */
    Macro_Clear_Area(GPIOA->PUPDR,
                     0x3Fu,
                     LED_PIN_START * 2);

    /* 처음에는 모두 OFF */
    Macro_Clear_Area(GPIOA->ODR,
                     LED_MASK,
                     LED_PIN_START);
}

void LED_On(unsigned int led)
{
    unsigned int pin;

    if ((led < 1u) || (led > LED_COUNT))
    {
        return;
    }

    /* LED1→PA5, LED2→PA6, LED3→PA7 */
    pin = led + 4u;

    Macro_Set_Bit(GPIOA->ODR, pin);
}

void LED_Off(unsigned int led)
{
    unsigned int pin;

    if ((led < 1u) || (led > LED_COUNT))
    {
        return;
    }

    pin = led + 4u;

    Macro_Clear_Bit(GPIOA->ODR, pin);
}

void LED_Display(unsigned int data)
{
    /*
     * data 하위 3비트 출력
     *
     * 001 → LED1
     * 010 → LED2
     * 100 → LED3
     * 111 → 전부 ON
     */
    Macro_Write_Block(GPIOA->ODR,
                      LED_MASK,
                      data & LED_MASK,
                      LED_PIN_START);
}