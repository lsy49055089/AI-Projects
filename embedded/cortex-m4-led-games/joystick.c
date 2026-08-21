#include "device_driver.h"

/*
 * 조이스틱 연결
 *
 * VRx -> CN8 A0 = PA0 = ADC1_IN0
 * VRy -> CN8 A1 = PA1 = ADC1_IN1
 * SW  -> CN8 A2 = PA4
 */

#define JOYSTICK_X_CHANNEL       0u
#define JOYSTICK_Y_CHANNEL       1u
#define JOYSTICK_SW_PIN          4u



#define JOYSTICK_SAMPLE_MS       10u

/* 중앙에서 이만큼 움직여야 방향 입력 */
#define JOYSTICK_MOVE_DELTA      900

/* 중앙 복귀 판정 범위 */
#define JOYSTICK_CENTER_DELTA    350

/* 같은 방향이 80ms 유지돼야 입력 */
#define JOYSTICK_STABLE_COUNT    8u

/* 중앙 상태가 200ms 유지돼야 중앙 인정 */
#define JOYSTICK_CENTER_COUNT    20u


static unsigned int Joystick_Center_X = 2048u;
static unsigned int Joystick_Center_Y = 2048u;


static unsigned int Joystick_Read_ADC(unsigned int channel)
{
    unsigned int value;

    /*
     * 변환할 채널 선택
     * SQ1에 채널 번호 저장
     */
    ADC1->SQR3 = channel;

    /*
     * 이전 EOC 플래그 정리
     */
    Macro_Clear_Bit(ADC1->SR, 1);

    /*
     * SWSTART = 1
     * ADC 변환 시작
     */
    Macro_Set_Bit(ADC1->CR2, 30);

    /*
     * EOC가 1이 될 때까지 대기
     */
    while (!Macro_Check_Bit_Set(ADC1->SR, 1))
    {
    }

    value = ADC1->DR;

    return value;
}


void Joystick_Init(void)
{
    /*
     * GPIOA Clock Enable
     */
    Macro_Set_Bit(RCC->AHB1ENR, 0);

    /*
     * PA0 = Analog mode
     * PA1 = Analog mode
     */
    Macro_Write_Block(GPIOA->MODER,
                      0x3u,
                      0x3u,
                      0u * 2u);

    Macro_Write_Block(GPIOA->MODER,
                      0x3u,
                      0x3u,
                      1u * 2u);

    /*
     * PA0, PA1 No Pull-up/Pull-down
     */
    Macro_Write_Block(GPIOA->PUPDR,
                      0x3u,
                      0x0u,
                      0u * 2u);

    Macro_Write_Block(GPIOA->PUPDR,
                      0x3u,
                      0x0u,
                      1u * 2u);

    /*
     * PA4 = 조이스틱 SW 입력
     */
    Macro_Write_Block(GPIOA->MODER,
                      0x3u,
                      0x0u,
                      JOYSTICK_SW_PIN * 2u);

    /*
     * SW Pull-up
     *
     * 안 누름 = 1
     * 누름   = 0
     */
    Macro_Write_Block(GPIOA->PUPDR,
                      0x3u,
                      0x1u,
                      JOYSTICK_SW_PIN * 2u);

    /*
     * ADC1 Clock Enable
     * APB2ENR bit 8
     */
    Macro_Set_Bit(RCC->APB2ENR, 8);

    /*
     * ADC Clock = PCLK2 / 4
     */
    Macro_Write_Block(ADC->CCR,
                      0x3u,
                      0x1u,
                      16u);

    /*
     * ADC 기본 설정
     * 12bit, Single Conversion
     */
    ADC1->CR1 = 0u;
    ADC1->CR2 = 0u;

    /*
     * Regular conversion 1개
     */
    ADC1->SQR1 = 0u;

    /*
     * Channel 0 Sampling Time = 480 cycles
     */
    Macro_Write_Block(ADC1->SMPR2,
                      0x7u,
                      0x7u,
                      0u);

    /*
     * Channel 1 Sampling Time = 480 cycles
     */
    Macro_Write_Block(ADC1->SMPR2,
                      0x7u,
                      0x7u,
                      3u);

    /*
     * ADC ON
     */
    Macro_Set_Bit(ADC1->CR2, 0);

    TIM2_Delay(1u);
}


unsigned int Joystick_Read_X(void)
{
    return Joystick_Read_ADC(JOYSTICK_X_CHANNEL);
}


unsigned int Joystick_Read_Y(void)
{
    return Joystick_Read_ADC(JOYSTICK_Y_CHANNEL);
}


int Joystick_SW_Is_Pressed(void)
{
    if (!Macro_Check_Bit_Set(GPIOA->IDR,
                             JOYSTICK_SW_PIN))
    {
        return 1;
    }

    return 0;
}



void Joystick_Calibrate_Center(void)
{
    unsigned int i;

    unsigned int sum_x = 0u;
    unsigned int sum_y = 0u;

    /*
     * 조이스틱을 놓은 중앙 상태에서
     * 64회 측정하여 평균값 계산
     */
    for (i = 0u; i < 64u; i++)
    {
        sum_x += Joystick_Read_X();
        sum_y += Joystick_Read_Y();

        TIM2_Delay(10u);
    }

    Joystick_Center_X = sum_x / 64u;
    Joystick_Center_Y = sum_y / 64u;
}




int Joystick_Get_Direction(void)
{
    unsigned int x;
    unsigned int y;

    int dx;
    int dy;

    int abs_dx;
    int abs_dy;

    x = Joystick_Read_X();
    y = Joystick_Read_Y();

    dx = (int)x - (int)Joystick_Center_X;
    dy = (int)y - (int)Joystick_Center_Y;

    abs_dx = (dx < 0) ? -dx : dx;
    abs_dy = (dy < 0) ? -dy : dy;

    /*
     * 중앙 데드존
     */
    if ((abs_dx < JOYSTICK_MOVE_DELTA) &&
        (abs_dy < JOYSTICK_MOVE_DELTA))
    {
        return JOY_NONE;
    }

    /*
     * 대각선으로 움직여도
     * 더 크게 움직인 축 하나만 인정
     */
    if (abs_dx > abs_dy)
    {
        if (dx < 0)
        {
            return JOY_LEFT;
        }

        return JOY_RIGHT;
    }

    if (dy < 0)
    {
        return JOY_UP;
    }

    return JOY_DOWN;
}



void Joystick_Wait_Center(void)
{
    unsigned int x;
    unsigned int y;

    unsigned int center_count = 0u;

    int dx;
    int dy;

    int abs_dx;
    int abs_dy;

    while (center_count < JOYSTICK_CENTER_COUNT)
    {
        x = Joystick_Read_X();
        y = Joystick_Read_Y();

        dx = (int)x - (int)Joystick_Center_X;
        dy = (int)y - (int)Joystick_Center_Y;

        abs_dx = (dx < 0) ? -dx : dx;
        abs_dy = (dy < 0) ? -dy : dy;

        /*
         * 중앙 근처가 200ms 연속 유지돼야
         * 중앙 복귀로 인정
         */
        if ((abs_dx < JOYSTICK_CENTER_DELTA) &&
            (abs_dy < JOYSTICK_CENTER_DELTA))
        {
            center_count++;
        }
        else
        {
            center_count = 0u;
        }

        TIM2_Delay(JOYSTICK_SAMPLE_MS);
    }
}


/*
 * 방향 입력 1회 받기
 *
 * 방향을 계속 유지해도 한 번만 입력됨
 */
int Joystick_Wait_Direction(void)
{
    int direction;
    int previous_direction = JOY_NONE;

    unsigned int stable_count = 0u;

    /*
     * 입력 시작 전 중앙 확인
     */
    Joystick_Wait_Center();

    for (;;)
    {
        direction = Joystick_Get_Direction();

        if (direction == JOY_NONE)
        {
            previous_direction = JOY_NONE;
            stable_count = 0u;
        }
        else if (direction == previous_direction)
        {
            stable_count++;
        }
        else
        {
            previous_direction = direction;
            stable_count = 1u;
        }

        /*
         * 같은 방향이 80ms 유지될 때만 입력
         */
        if (stable_count >= JOYSTICK_STABLE_COUNT)
        {
            /*
             * 조이스틱을 중앙으로 놓아야
             * 함수가 끝나고 입력 1회 인정
             */
            Joystick_Wait_Center();

            return direction;
        }

        TIM2_Delay(JOYSTICK_SAMPLE_MS);
    }
}