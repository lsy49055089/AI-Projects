#include "device_driver.h"

/*
 * NUCLEO CN8 A3 = PB0
 */
#define BUZZER_PIN     0u


void Buzzer_Init(void)
{
    /* GPIOB Clock Enable */
    Macro_Set_Bit(RCC->AHB1ENR, 1);

    /* PB0 GPIO Output mode: MODER0 = 01 */
    Macro_Write_Block(GPIOB->MODER,
                      0x3u,
                      0x1u,
                      BUZZER_PIN * 2u);

    /* Push-Pull */
    Macro_Clear_Bit(GPIOB->OTYPER,
                    BUZZER_PIN);

    /* No Pull-up / Pull-down */
    Macro_Write_Block(GPIOB->PUPDR,
                      0x3u,
                      0x0u,
                      BUZZER_PIN * 2u);

    /* 처음에는 부저 OFF */
    Macro_Clear_Bit(GPIOB->ODR,
                    BUZZER_PIN);
}


void Buzzer_On(void)
{
    Macro_Set_Bit(GPIOB->ODR,
                  BUZZER_PIN);
}


void Buzzer_Off(void)
{
    Macro_Clear_Bit(GPIOB->ODR,
                    BUZZER_PIN);
}


static void Buzzer_Tone(unsigned int half_period_ms,
                        unsigned int duration_ms)
{
    unsigned int elapsed_ms = 0u;

    while (elapsed_ms < duration_ms)
    {
        Buzzer_On();
        TIM2_Delay(half_period_ms);

        Buzzer_Off();
        TIM2_Delay(half_period_ms);

        elapsed_ms += half_period_ms * 2u;
    }

    Buzzer_Off();
}


/* 정답음: 3단계 상승 */
void Buzzer_Correct(void)
{
    Buzzer_Tone(3u, 50u);
    TIM2_Delay(15u);

    Buzzer_Tone(2u, 60u);
    TIM2_Delay(15u);

    Buzzer_Tone(1u, 140u);
}


void Buzzer_Wrong(void)
{
    Buzzer_Tone(3u, 500u);
}


void Buzzer_Timeout(void)
{
    Buzzer_Tone(2u, 180u);

    TIM2_Delay(100u);

    Buzzer_Tone(2u, 180u);
}


void Buzzer_Clear(void)
{
    Buzzer_Tone(3u, 100u);
    Buzzer_Tone(2u, 100u);
    Buzzer_Tone(1u, 300u);
}


/*
 * 반응속도 게임 선택음
 * 낮은 음 → 높은 음
 */
void Buzzer_Select_Reaction(void)
{
    Buzzer_Tone(3u, 80u);
    TIM2_Delay(40u);

    Buzzer_Tone(1u, 120u);
}


/*
 * 기억력 게임 선택음
 * 높은 음 → 낮은 음
 */
void Buzzer_Select_Memory(void)
{
    Buzzer_Tone(1u, 80u);
    TIM2_Delay(40u);

    Buzzer_Tone(3u, 120u);
}


/*
 * 반응속도 게임 시작음
 * 카운트다운 느낌
 */
void Buzzer_Start_Reaction(void)
{
    Buzzer_Tone(2u, 70u);
    TIM2_Delay(60u);

    Buzzer_Tone(2u, 70u);
    TIM2_Delay(60u);

    Buzzer_Tone(2u, 70u);
    TIM2_Delay(80u);

    Buzzer_Tone(1u, 250u);
}


/*
 * 기억력 게임 시작음
 * 낮은 음부터 단계적으로 상승
 */
void Buzzer_Start_Memory(void)
{
    Buzzer_Tone(4u, 90u);
    TIM2_Delay(30u);

    Buzzer_Tone(3u, 90u);
    TIM2_Delay(30u);

    Buzzer_Tone(2u, 90u);
    TIM2_Delay(30u);

    Buzzer_Tone(1u, 180u);
}