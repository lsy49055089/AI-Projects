#include "device_driver.h"

/*
 * 외부 게임 버튼
 *
 * BTN1 : D8  = PA9
 * BTN2 : D9  = PC7
 * BTN3 : D10 = PB6
 *
 * 내부 Pull-up 사용
 * 안 누름 = 1
 * 누름    = 0
 */

#define BTN1_PIN            9u
#define BTN2_PIN            7u
#define BTN3_PIN            6u

#define DEBOUNCE_TIME_MS     5u


/*
 * TIM2와 SysTick을 건드리지 않는 지연 함수
 *
 * 게임 중:
 * TIM2    = 반응시간 측정
 * SysTick = 제한시간 측정
 *
 * 따라서 디바운스는 Cortex-M4의 DWT Cycle Counter 사용
 */
static void Button_Delay_ms(unsigned int msec)
{
    unsigned int start;
    unsigned int ticks;

    ticks = (HCLK / 1000u) * msec;
    start = DWT->CYCCNT;

    while ((unsigned int)(DWT->CYCCNT - start) < ticks)
    {
    }
}


void Button_Init(void)
{
    /*
     * GPIOA, GPIOB, GPIOC Clock Enable
     */
    Macro_Set_Bit(RCC->AHB1ENR, 0);
    Macro_Set_Bit(RCC->AHB1ENR, 1);
    Macro_Set_Bit(RCC->AHB1ENR, 2);


    /*
     * BTN1: D8 = PA9
     * 입력 모드 + Pull-up
     */
    Macro_Write_Block(GPIOA->MODER,
                      0x3,
                      0x0,
                      BTN1_PIN * 2);

    Macro_Write_Block(GPIOA->PUPDR,
                      0x3,
                      0x1,
                      BTN1_PIN * 2);


    /*
     * BTN2: D9 = PC7
     * 입력 모드 + Pull-up
     */
    Macro_Write_Block(GPIOC->MODER,
                      0x3,
                      0x0,
                      BTN2_PIN * 2);

    Macro_Write_Block(GPIOC->PUPDR,
                      0x3,
                      0x1,
                      BTN2_PIN * 2);


    /*
     * BTN3: D10 = PB6
     * 입력 모드 + Pull-up
     */
    Macro_Write_Block(GPIOB->MODER,
                      0x3,
                      0x0,
                      BTN3_PIN * 2);

    Macro_Write_Block(GPIOB->PUPDR,
                      0x3,
                      0x1,
                      BTN3_PIN * 2);


    /*
     * Cortex-M4 DWT Cycle Counter Enable
     */
    CoreDebug->DEMCR |= CoreDebug_DEMCR_TRCENA_Msk;

    DWT->CYCCNT = 0u;

    DWT->CTRL |= DWT_CTRL_CYCCNTENA_Msk;
}


/*
 * 현재 눌린 버튼을 즉시 확인
 *
 * 반환값:
 * BTN_NONE
 * BTN1
 * BTN2
 * BTN3
 * BTN_MULTI
 */
int Button_Get_Raw(void)
{
    unsigned int pressed = 0u;

    /*
     * 내부 Pull-up이므로
     * 안 누름 = 1
     * 누름    = 0
     */

    /* BTN1: D8 = PA9 */
    if (!Macro_Check_Bit_Set(GPIOA->IDR, BTN1_PIN))
    {
        pressed |= 0x1u;
    }

    /* BTN2: D9 = PC7 */
    if (!Macro_Check_Bit_Set(GPIOC->IDR, BTN2_PIN))
    {
        pressed |= 0x2u;
    }

    /* BTN3: D10 = PB6 */
    if (!Macro_Check_Bit_Set(GPIOB->IDR, BTN3_PIN))
    {
        pressed |= 0x4u;
    }

    switch (pressed)
    {
        case 0x0u:
            return BTN_NONE;

        case 0x1u:
            return BTN1;

        case 0x2u:
            return BTN2;

        case 0x4u:
            return BTN3;

        default:
            return BTN_MULTI;
    }
}


/*
 * 최초 입력 후 5ms 뒤에도 같은 버튼이면
 * 정상적인 입력으로 확정
 */
/*
 * 최초 입력 후 5ms 기다린 다음
 * 안정된 버튼 번호를 반환
 *
 * 반환값:
 * BTN1, BTN2, BTN3 : 정상 입력
 * BTN_NONE         : 입력 불안정
 */
int Button_Confirm_Pressed(int first_button)
{
    int confirmed_button;

    if (first_button == BTN_NONE)
    {
        return BTN_NONE;
    }

    /*
     * 접점이 안정될 때까지 대기
     */
    Button_Delay_ms(DEBOUNCE_TIME_MS);

    /*
     * 5ms 후 값을 실제 입력으로 사용
     */
    confirmed_button = Button_Get_Raw();

    if ((confirmed_button >= BTN1) &&
        (confirmed_button <= BTN3))
    {
        return confirmed_button;
    }

    /*
     * BTN_NONE 또는 BTN_MULTI면 입력 무시
     */
    return BTN_NONE;
}


/*
 * 모든 버튼이 확실히 떨어질 때까지 대기
 */
void Button_Wait_All_Released(void)
{
    for (;;)
    {
        while (Button_Get_Raw() != BTN_NONE)
        {
        }

        Button_Delay_ms(DEBOUNCE_TIME_MS);

        if (Button_Get_Raw() == BTN_NONE)
        {
            return;
        }
    }
}

/*
 * NUCLEO On-board USER Button
 *
 * PC13
 * 안 누름 = 1
 * 누름    = 0
 */

#define USER_KEY_PIN    13u

void Key_Poll_Init(void)
{
    /* GPIOC Clock Enable */
    Macro_Set_Bit(RCC->AHB1ENR, 2);

    /* PC13 입력 모드: MODER = 00 */
    Macro_Write_Block(GPIOC->MODER,
                      0x3u,
                      0x0u,
                      USER_KEY_PIN * 2u);

    /*
     * PC13 Pull-up
     * 안 누르면 HIGH, 누르면 LOW
     */
    Macro_Write_Block(GPIOC->PUPDR,
                      0x3u,
                      0x1u,
                      USER_KEY_PIN * 2u);
}


int Key_Get_Pressed(void)
{
    /*
     * PC13이 0이면 눌린 상태
     */
    if (Macro_Check_Bit_Clear(GPIOC->IDR, USER_KEY_PIN))
    {
        return 1;
    }

    return 0;
}


void Key_Wait_Key_Pressed(void)
{
    while (!Key_Get_Pressed())
    {
    }

    /* 눌림 디바운스 */
    Button_Delay_ms(20u);

    while (!Key_Get_Pressed())
    {
    }
}


void Key_Wait_Key_Released(void)
{
    while (Key_Get_Pressed())
    {
    }

    /* 뗌 디바운스 */
    Button_Delay_ms(20u);

    while (Key_Get_Pressed())
    {
    }
}