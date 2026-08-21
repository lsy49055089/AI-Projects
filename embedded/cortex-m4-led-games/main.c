#include "device_driver.h"
#include <stdio.h>


#define TOTAL_ROUNDS             10u

#define LIMIT_START_MS    		1000u
#define LIMIT_STEP_MS       	50u	

#define RANDOM_WAIT_MIN_MS       700u
#define RANDOM_WAIT_RANGE_MS     1001u

#define WAIT_POLL_MS             5u
#define ROUND_GAP_MS             100u


#define RESULT_CORRECT           1
#define RESULT_WRONG             0
#define RESULT_TIMEOUT          -1

#define GAME_REACTION            1
#define GAME_MEMORY              2

/*
 * 버튼과 LED의 물리적인 위치가 반대이므로
 * BTN1과 BTN3의 LED 매핑을 뒤집음
 *
 * BTN1 -> LED3
 * BTN2 -> LED2
 * BTN3 -> LED1
 */
static const unsigned int Button_To_LED[5] =
{
    0u,     /* BTN_NONE  */
    3u,     /* BTN1 -> LED3 */
    2u,     /* BTN2 -> LED2 */
    1u,     /* BTN3 -> LED1 */
    0u      /* BTN_MULTI */
};


static unsigned int Random_State = 0x13579BDFu;


static void Sys_Init(int baud)
{
    SCB->CPACR |= (0x3u << 20) |
                  (0x3u << 22);

    Clock_Init();
    Uart2_Init(baud);
    setvbuf(stdout, NULL, _IONBF, 0);

    LED_Init();

    /* D8, D9, D10 외부 버튼 */
    Button_Init();

    /* 파란색 USER 버튼 PC13 */
    Key_Poll_Init();
	Buzzer_Init();
}


/*
 * 간단한 난수 생성기
 */
static unsigned int Random_Next(void)
{
    Random_State ^= Random_State << 13;
    Random_State ^= Random_State >> 17;
    Random_State ^= Random_State << 5;

    return Random_State;
}


/*
 * USER 버튼을 누르는 시점을 이용해
 * 난수 초기값을 바꿈
 */
static void Wait_User_Key_And_Seed(void)
{
    unsigned int seed = 0x13579BDFu;

    printf("\nPress USER button to start\n");

    while (!Key_Get_Pressed())
    {
        seed++;

        if (seed == 0u)
        {
            seed = 0x13579BDFu;
        }
    }

    /* 눌림 디바운스 */
    TIM2_Delay(20);

    /*
     * 20ms 뒤에도 눌려 있지 않다면
     * 잡음이므로 다시 기다림
     */
    if (!Key_Get_Pressed())
    {
        Wait_User_Key_And_Seed();
        return;
    }

    /* 버튼에서 손을 뗄 때까지 대기 */
    while (Key_Get_Pressed())
    {
        seed++;
    }

    /* 뗌 디바운스 */
    TIM2_Delay(20);

    Random_State ^= seed;

    if (Random_State == 0u)
    {
        Random_State = 0x13579BDFu;
    }

    printf("USER BUTTON OK\n");
}


/*
 * LED 번호를 LED_Display용 비트값으로 변환
 *
 * LED1 -> 001
 * LED2 -> 010
 * LED3 -> 100
 */
static unsigned int LED_To_Mask(unsigned int led)
{
    return 1u << (led - 1u);
}

// static void Blink_Correct_LED(unsigned int led)
// {
//     unsigned int i;
//     unsigned int mask;

//     mask = LED_To_Mask(led);

//     for (i = 0u; i < 2u; i++)
//     {
//         LED_Display(mask);
//         TIM2_Delay(100);

//         LED_Display(0u);
//         TIM2_Delay(100);
//     }
// }
/*
 * 직전 LED와 다른 LED 선택
 */
static unsigned int Select_Next_LED(unsigned int previous_led)
{
    unsigned int next_led;

    do
    {
        next_led = (Random_Next() % 3u) + 1u;
    }
    while (next_led == previous_led);

    return next_led;
}


/*
 * LED가 켜지기 전 랜덤 대기
 *
 * 대기 중 버튼을 누르면 반칙
 */
static int Wait_Random_Time(unsigned int wait_ms)
{
    unsigned int elapsed_ms = 0u;

    int raw;


    while (elapsed_ms < wait_ms)
    {
        raw = Button_Get_Raw();


        if (raw != BTN_NONE)
        {
            if (Button_Confirm_Pressed(raw))
            {
                Button_Wait_All_Released();

                return 0;
            }
        }


        TIM2_Delay(WAIT_POLL_MS);

        elapsed_ms += WAIT_POLL_MS;
    }


    return 1;
}


/*
 * LED가 켜진 뒤 버튼 입력 처리
 */
/*
 * LED가 켜진 뒤 버튼 입력 처리
 *
 * TIM2 하나로:
 * 1. 반응시간 측정
 * 2. 제한시간 확인
 *
 * 기존 SysTick은 여기서 사용하지 않음
 */
static int Play_Reaction(unsigned int target_led,
                         unsigned int limit_ms,
                         unsigned int *reaction_ms,
                         int *pressed_button)
{
    int raw;
	//int confirmed_button;

    unsigned int first_contact_us;
    unsigned int elapsed_us;
    unsigned int limit_us;

    *reaction_ms = 0u;
    *pressed_button = BTN_NONE;

    limit_us = limit_ms * 1000u;

    /*
     * 목표 LED ON
     */
    LED_Display(LED_To_Mask(target_led));

    /*
     * 반응시간 측정 시작
     */
    TIM2_Stopwatch_Start();

    for (;;)
    {
        /*
         * 버튼을 먼저 확인
         *
         * 제한시간 끝부분에서 버튼을 눌러도
         * 최초 접촉 시점을 먼저 저장하기 위함
         */
		raw = Button_Get_Raw();

		if (raw != BTN_NONE)
		{
			/*
			* 버튼이 처음 눌린 시각 저장
			*/
			first_contact_us = TIM2_Stopwatch_Get_Time();

			/*
			* 반응 게임에서는 최초 LOW를 즉시 입력으로 인정
			*/
			TIM2_Stopwatch_Stop();

			LED_Display(0u);

			*reaction_ms =
				(first_contact_us + 500u) / 1000u;

			*pressed_button = raw;

			printf("INPUT: BTN%d, %u ms\n",
				raw,
				*reaction_ms);

			/*
			* 버튼이 확실히 떨어질 때까지 기다림
			* 이 함수 안에는 5ms 뗌 디바운스가 있음
			*/
			Button_Wait_All_Released();

			if (first_contact_us > limit_us)
			{
				return RESULT_TIMEOUT;
			}

			if ((raw >= BTN1) &&
				(raw <= BTN3) &&
				(Button_To_LED[raw] == target_led))
			{
				return RESULT_CORRECT;
			}

			return RESULT_WRONG;
		}

        /*
         * 아무 버튼도 감지하지 못한 상태에서
         * 제한시간 초과 확인
         */
        elapsed_us = TIM2_Stopwatch_Get_Time();

        if (elapsed_us >= limit_us)
        {
            TIM2_Stopwatch_Stop();

            LED_Display(0u);

            return RESULT_TIMEOUT;
        }
    }
}


/*
 * 모든 LED 깜빡임
 */
static void Blink_All(unsigned int count,
                      unsigned int interval_ms)
{
    unsigned int i;


    for (i = 0u; i < count; i++)
    {
        LED_Display(0x7u);

        TIM2_Delay(interval_ms);


        LED_Display(0x0u);

        TIM2_Delay(interval_ms);
    }
}


static void Game_Over_Hold(void)
{
    SysTick_Stop();

    /* 111 = LED 3개 전체 ON */
    LED_Display(0x7u);

    printf("PRESS RESET BUTTON TO RESTART\n");

    for (;;)
    {
    }
}

/*
 * 10라운드 게임
 */
static void Run_Game(void)
{
    unsigned int round;

    unsigned int limit_ms;

    unsigned int wait_ms;

    unsigned int target_led;

    unsigned int previous_led = 0u;

    unsigned int reaction_ms;

    int pressed_button;

    int result;


    LED_Display(0u);

    Button_Wait_All_Released();


    printf("\n==============================\n");

    printf(" LED REACTION GAME - 10 ROUND\n");

    printf(" BTN1->LED3, BTN2->LED2, BTN3->LED1\n");

    printf(" Limit: 1000ms -> 550ms\n");

    printf("==============================\n");


    for (round = 1u;
         round <= TOTAL_ROUNDS;
         round++)
    {
        /*
         * 라운드마다 50ms씩 감소
         *
         * Round 1  = 1000ms
         * Round 2  = 950ms
         * ...
         * Round 10 = 550ms
         */
        limit_ms =
            LIMIT_START_MS -
            ((round - 1u) * LIMIT_STEP_MS);


        /*
         * 라운드 사이에는 LED OFF
         */
        LED_Display(0u);

        TIM2_Delay(ROUND_GAP_MS);

        Button_Wait_All_Released();


        printf("\n[ROUND %u/%u] LIMIT = %u ms\n",
               round,
               TOTAL_ROUNDS,
               limit_ms);


		Game_LCD_Show_Wait(round,
                   TOTAL_ROUNDS,
                   limit_ms);


        printf("WAIT... do not press early\n");


        /*
         * 700~1700ms 랜덤 대기
         */
        wait_ms =
            RANDOM_WAIT_MIN_MS +
            (Random_Next() %
             RANDOM_WAIT_RANGE_MS);

		/*
		* 700~1700ms 랜덤 대기 중 버튼을 누르면 반칙
		*/
		if (!Wait_Random_Time(wait_ms))
		{
			printf("TOO EARLY! GAME OVER at round %u\n",
				round);

			Game_LCD_Show_Early();
			Buzzer_Wrong();

			Game_Over_Hold();
		}

/*
 * 랜덤 대기의 마지막 검사와
 * 목표 LED가 켜지는 순간 사이에
 * 버튼이 눌리는 것을 방지
 */
		if (Button_Get_Raw() != BTN_NONE)
		{
			printf("TOO EARLY! GAME OVER at round %u\n",
				round);

			Game_LCD_Show_Early();
			Buzzer_Wrong();

			Game_Over_Hold();
		}

		/*
		* 10ms 동안 모든 버튼이 계속
		* 떨어져 있는 상태인지 확인
		*/
		TIM2_Delay(10u);

		if (Button_Get_Raw() != BTN_NONE)
		{
			printf("TOO EARLY! GAME OVER at round %u\n",
				round);

			Game_LCD_Show_Early();
			Buzzer_Wrong();

			Game_Over_Hold();
		}
        /*
         * 직전과 다른 LED 선택
         */
        target_led =
            Select_Next_LED(previous_led);

        previous_led = target_led;


        printf("GO! LED%u ON\n",
               target_led);

			   
		Game_LCD_Show_Go(target_led,
                 4u - target_led);

        result =
            Play_Reaction(target_led,
                          limit_ms,
                          &reaction_ms,
                          &pressed_button);


        /*
         * 정답
         */
		if (result == RESULT_CORRECT)
		{
			printf("CORRECT: BTN%d -> LED%u, %u ms\n",
				pressed_button,
				target_led,
				reaction_ms);


			
			Game_LCD_Show_Correct(reaction_ms);
			Buzzer_Correct();
			/*
			* 정답일 때만
			* LED 3개 전체를 두 번 깜빡임
			*/
			Blink_All(2u, 120u);

			/*
			* USER 버튼 없이 다음 라운드 진행
			*/
			continue;
		}


        /*
         * 제한시간 초과
         */
        if (result == RESULT_TIMEOUT)
        {
            printf("TIME OUT! LIMIT = %u ms\n",
                   limit_ms);

			Game_LCD_Show_Timeout(limit_ms);

			Buzzer_Timeout();
        }

		

        /*
         * 오답
         */
		else
		{
			Buzzer_Wrong();

			if (pressed_button == BTN_MULTI)
			{
				printf("WRONG: multiple buttons pressed\n");

				LCD_Print_Line(0u, "WRONG BUTTON!");
				LCD_Print_Line(1u, "MULTIPLE INPUT");
			}
			else
			{
				printf("WRONG: BTN%d maps to LED%u, "
					"target was LED%u\n",
					pressed_button,
					Button_To_LED[pressed_button],
					target_led);

				Game_LCD_Show_Wrong(pressed_button,
									4u - target_led);
			}
		}


        printf("GAME OVER at round %u\n",
               round);

        Game_Over_Hold();
    }


    /*
     * 10라운드 전부 성공
     */
	printf("\nALL 10 ROUNDS CLEAR!\n");

	Game_LCD_Show_Clear(0u);

	Buzzer_Clear();

	Blink_All(5u, 100u);
}



static int Menu_Select_Game(void)
{
    int button;

    LED_Display(0u);

    Button_Wait_All_Released();

    LCD_Print_Line(0u, "SELECT GAME");
    LCD_Print_Line(1u, "<REACT  MEMORY>");

    printf("\n========================\n");
    printf("SELECT GAME\n");
    printf("LEFT  BTN1 : REACTION\n");
    printf("RIGHT BTN3 : MEMORY\n");
    printf("========================\n");

    for (;;)
    {
        button = Button_Get_Raw();

        if (button == BTN_NONE)
        {
            continue;
        }

        if (button == BTN_MULTI)
        {
            printf("MENU: MULTI BUTTON\n");

            Button_Wait_All_Released();

            continue;
        }

        /*
         * 왼쪽 버튼
         * → 반응속도 게임 선택
         */
        if (button == BUTTON_LEFT)
        {
            printf("MENU: LEFT -> REACTION\n");

            LCD_Print_Line(0u, "REACTION GAME");
            LCD_Print_Line(1u, "PRESS USER");

            Button_Wait_All_Released();

            Buzzer_Select_Reaction();

            return GAME_REACTION;
        }

        /*
         * 오른쪽 버튼
         * → 기억력 게임 선택
         */
        if (button == BUTTON_RIGHT)
        {
            printf("MENU: RIGHT -> MEMORY\n");

            LCD_Print_Line(0u, "MEMORY GAME");
            LCD_Print_Line(1u, "PRESS USER");

            Button_Wait_All_Released();

            Buzzer_Select_Memory();

            return GAME_MEMORY;
        }

        /*
         * 가운데 버튼은 메뉴에서 무시
         */
        if (button == BUTTON_MIDDLE)
        {
            printf("MENU: MIDDLE BUTTON IGNORED\n");

            Button_Wait_All_Released();
        }
    }
}


// void Main(void)
// {
//     int selected_game;

//     Sys_Init(115200);

//     LCD_Init();

//     if (!LCD_Is_Ready())
//     {
//         printf("LCD I2C ERROR\n");

//         for (;;)
//         {
//         }
//     }

//     /*
//      * 조이스틱 ADC 및 SW 초기화
//      */
//     Joystick_Init();

//     LCD_Print_Line(0u, "CENTER STICK");
//     LCD_Print_Line(1u, "PLEASE WAIT...");

//     /*
//     * RESET 후 이때 조이스틱에서 손을 놓고
//     * 중앙에 둬야 함
//     */
//     TIM2_Delay(500u);

//     Joystick_Calibrate_Center();

//     printf("\nMINI GAME CONSOLE\n");

//     /*
//      * 조이스틱으로 게임 선택
//      */
//     selected_game =
//         Menu_Select_Game();

//     /*
//      * USER 버튼으로 선택한 게임 시작
//      *
//      * 기존 반응 게임 난수 초기값도 함께 설정됨
//      */
//     Wait_User_Key_And_Seed();


//     /*
//      * 반응속도 게임
//      */
//     if (selected_game == GAME_REACTION)
//     {
//         Run_Game();
//     }

//     /*
//      * 기억력 게임
//      */
//     else
//     {
//         Run_Memory_Game();
//     }


//     /*
//      * 게임이 정상 종료된 경우
//      */
//     LCD_Print_Line(0u, "GAME FINISHED");
//     LCD_Print_Line(1u, "PRESS RESET");

//     printf("PRESS RESET BUTTON TO RETURN MENU\n");

//     for (;;)
//     {
//     }
// }


// void Main(void)
// {
//     int selected_game;

//     Sys_Init(115200);

//     LCD_Init();

//     if (!LCD_Is_Ready())
//     {
//         printf("LCD I2C ERROR\n");

//         for (;;)
//         {
//         }
//     }

//     printf("\nMINI GAME CONSOLE\n");


//     /*
//      * 외부 왼쪽/오른쪽 버튼으로 게임 선택
//      */
//     selected_game =
//         Menu_Select_Game();


//     /*
//      * 선택 후 파란색 USER 버튼으로 시작
//      */
//     Wait_User_Key_And_Seed();


//     /*
//      * 반응속도 게임
//      */
//     if (selected_game == GAME_REACTION)
//     {
//         Run_Game();
//     }

//     /*
//      * 기억력 게임
//      */
//     else
//     {
//         Run_Memory_Game();
//     }


//     LCD_Print_Line(0u, "GAME FINISHED");
//     LCD_Print_Line(1u, "PRESS RESET");

//     printf("PRESS RESET BUTTON TO RETURN MENU\n");

//     for (;;)
//     {
//     }
// }



void Main(void)
{
    int selected_game;

    Sys_Init(115200);

    LCD_Init();

    if (!LCD_Is_Ready())
    {
        printf("LCD I2C ERROR\n");

        for (;;)
        {
        }
    }

    printf("\nMINI GAME CONSOLE START\n");

    /*
     * 외부 버튼으로 게임 선택
     */
    selected_game = Menu_Select_Game();

    printf("GAME SELECTED = %d\n", selected_game);
    printf("PRESS BLUE USER BUTTON\n");

    /*
     * NUCLEO 파란 USER 버튼으로 시작
     */
    Wait_User_Key_And_Seed();

    /*
     * 반응속도 게임
     */
    if (selected_game == GAME_REACTION)
    {
        printf("REACTION GAME START\n");

        LCD_Print_Line(0u, "REACTION GAME");
        LCD_Print_Line(1u, "GAME START!");

        Buzzer_Start_Reaction();

        TIM2_Delay(300u);

        Run_Game();
    }

    /*
     * 기억력 게임
     */
    else
    {
        printf("MEMORY GAME START\n");

        LCD_Print_Line(0u, "MEMORY GAME");
        LCD_Print_Line(1u, "GAME START!");

        Buzzer_Start_Memory();

        TIM2_Delay(300u);

        Run_Memory_Game();
    }

    LCD_Print_Line(0u, "GAME FINISHED");
    LCD_Print_Line(1u, "PRESS RESET");

    for (;;)
    {
    }
}