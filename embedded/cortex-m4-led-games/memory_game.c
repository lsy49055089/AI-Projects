#include "device_driver.h"
#include <stdio.h>


#define MEMORY_MAX_LEVEL          16u

#define MEMORY_SHOW_MS            600u
#define MEMORY_SHOW_GAP_MS        250u
#define MEMORY_RESULT_HOLD_MS     1200u


#define MEMORY_INVALID            0
#define MEMORY_LEFT               1
#define MEMORY_MIDDLE             2
#define MEMORY_RIGHT              3


static unsigned int Memory_Random_State = 0x2468ACE1u;


/*
 * LCD 한 줄용 16칸 공백 문자열 생성
 */
static void Memory_Clear_Line_Buffer(char *line)
{
    unsigned int i;

    for (i = 0u; i < 16u; i++)
    {
        line[i] = ' ';
    }

    line[16] = '\0';
}


/*
 * 기억력 게임 입력값을 문자로 변환
 */
static char Memory_Input_To_Char(int input)
{
    switch (input)
    {
        case MEMORY_LEFT:
            return 'L';

        case MEMORY_MIDDLE:
            return 'M';

        case MEMORY_RIGHT:
            return 'R';

        default:
            return 'X';
    }
}


/*
 * 실제 버튼 번호를 기억력 게임 입력값으로 변환
 */
static int Memory_Button_To_Input(int button)
{
    if (button == BUTTON_LEFT)
    {
        return MEMORY_LEFT;
    }

    if (button == BUTTON_MIDDLE)
    {
        return MEMORY_MIDDLE;
    }

    if (button == BUTTON_RIGHT)
    {
        return MEMORY_RIGHT;
    }

    return MEMORY_INVALID;
}


/*
 * 기억력 게임 난수 생성기
 */
static unsigned int Memory_Random_Next(void)
{
    Memory_Random_State ^=
        Memory_Random_State << 13;

    Memory_Random_State ^=
        Memory_Random_State >> 17;

    Memory_Random_State ^=
        Memory_Random_State << 5;

    return Memory_Random_State;
}


/*
 * USER 버튼을 누른 시점으로 난수값 변화
 *
 * Button_Init()에서 DWT Cycle Counter가 이미 시작됨
 */
static void Memory_Random_Seed(void)
{
    unsigned int seed;

    seed = DWT->CYCCNT;

    Memory_Random_State ^= seed;
    Memory_Random_State ^= seed << 7;
    Memory_Random_State ^= seed >> 3;

    if (Memory_Random_State == 0u)
    {
        Memory_Random_State = 0x2468ACE1u;
    }
}


/*
 * L, M, R 중 하나 생성
 */
static int Memory_Create_Input(void)
{
    return (int)((Memory_Random_Next() % 3u) + 1u);
}


/*
 * USER 버튼 1회 입력 대기
 */
static void Memory_Wait_User_Button(void)
{
    for (;;)
    {
        while (!Key_Get_Pressed())
        {
        }

        TIM2_Delay(20u);

        if (Key_Get_Pressed())
        {
            break;
        }
    }

    while (Key_Get_Pressed())
    {
    }

    TIM2_Delay(20u);
}


/*
 * 외부 버튼 입력 1회 받기
 *
 * 버튼을 계속 누르고 있어도
 * 손을 뗄 때까지 기다리므로 1번만 입력됨
 */


static int Memory_Wait_Game_Button(void)
{
    int button;
    int input;

    for (;;)
    {
        button = Button_Get_Raw();

        if (button == BTN_NONE)
        {
            continue;
        }

        if (button == BTN_MULTI)
        {
            printf("MEMORY INPUT: MULTI\n");

            Button_Wait_All_Released();

            return MEMORY_INVALID;
        }

        if (button == BUTTON_LEFT)
        {
            input = MEMORY_LEFT;

            printf("MEMORY INPUT: LEFT\n");
        }
        else if (button == BUTTON_MIDDLE)
        {
            input = MEMORY_MIDDLE;

            printf("MEMORY INPUT: MIDDLE\n");
        }
        else if (button == BUTTON_RIGHT)
        {
            input = MEMORY_RIGHT;

            printf("MEMORY INPUT: RIGHT\n");
        }
        else
        {
            input = MEMORY_INVALID;
        }

        Button_Wait_All_Released();

        return input;
    }
}

/*
 * 현재 레벨 안내
 */
static void Memory_Show_Level(unsigned int level)
{
    char line[17];

    snprintf(line,
             sizeof(line),
             "LEVEL %u / %u",
             level,
             MEMORY_MAX_LEVEL);

    LCD_Print_Line(0u, line);
    LCD_Print_Line(1u, "WATCH...");
}


/*
 * 문제 수열을 한 글자씩 표시
 *
 * LEVEL 3 수열이 L, M, R이면:
 *
 * L 표시 후 지움
 * 두 번째 칸에 M 표시 후 지움
 * 세 번째 칸에 R 표시 후 지움
 */
static void Memory_Show_Sequence(const int *sequence,
                                 unsigned int level)
{
    unsigned int i;

    char top_line[17];
    char bottom_line[17];

    Memory_Clear_Line_Buffer(top_line);
    Memory_Clear_Line_Buffer(bottom_line);

    LCD_Print_Line(0u, top_line);
    LCD_Print_Line(1u, bottom_line);

    TIM2_Delay(300u);

    for (i = 0u; i < level; i++)
    {
        Memory_Clear_Line_Buffer(top_line);

        top_line[i] =
            Memory_Input_To_Char(sequence[i]);

        LCD_Print_Line(0u, top_line);
        LCD_Print_Line(1u, bottom_line);

        TIM2_Delay(MEMORY_SHOW_MS);

        /*
         * 현재 문제 문자 지우기
         */
        Memory_Clear_Line_Buffer(top_line);

        LCD_Print_Line(0u, top_line);

        TIM2_Delay(MEMORY_SHOW_GAP_MS);
    }
}


/*
 * 사용자 입력 처리
 *
 * 입력할 때마다:
 *
 * 윗줄 = 해당 위치 정답
 * 아랫줄 = 사용자가 누른 버튼
 */
static int Memory_Input_Sequence(const int *sequence,
                                 unsigned int level)
{
    unsigned int i;

    int input;

    char top_line[17];
    char bottom_line[17];

    Memory_Clear_Line_Buffer(top_line);
    Memory_Clear_Line_Buffer(bottom_line);

    LCD_Print_Line(0u, top_line);
    LCD_Print_Line(1u, bottom_line);

    Button_Wait_All_Released();

    for (i = 0u; i < level; i++)
    {
        input =
            Memory_Wait_Game_Button();

        /*
         * 입력 한 번마다 이번 위치의
         * 정답과 입력값을 동시에 공개
         */
        top_line[i] =
            Memory_Input_To_Char(sequence[i]);

        bottom_line[i] =
            Memory_Input_To_Char(input);

        LCD_Print_Line(0u, top_line);
        LCD_Print_Line(1u, bottom_line);

        /*
         * 틀린 순간 종료
         */
        if (input != sequence[i])
        {
            return 0;
        }

        TIM2_Delay(120u);
    }

    return 1;
}


/*
 * 기억력 게임 실행
 */
void Run_Memory_Game(void)
{
    int sequence[MEMORY_MAX_LEVEL];

    unsigned int level;

    char line[17];

    int correct;


    Memory_Random_Seed();

    level = 1u;

    sequence[0] =
        Memory_Create_Input();


    for (;;)
    {
        /*
         * 현재 레벨 표시
         */
        Memory_Show_Level(level);

        TIM2_Delay(800u);


        /*
         * 문제 표시
         */
        Memory_Show_Sequence(sequence,
                             level);


        /*
         * 입력 안내
         */
        LCD_Print_Line(0u, "YOUR TURN");
        LCD_Print_Line(1u, "L     M      R");

        TIM2_Delay(500u);


        /*
         * 버튼 입력
         */
        correct =
            Memory_Input_Sequence(sequence,
                                  level);


        /*
         * 오답
         */
        if (!correct)
        {
            Buzzer_Wrong();

            /*
             * 정답과 사용자 입력을 잠깐 유지
             */
            TIM2_Delay(MEMORY_RESULT_HOLD_MS);

            snprintf(line,
                     sizeof(line),
                     "WRONG! LEVEL %u",
                     level);

            LCD_Print_Line(0u, line);
            LCD_Print_Line(1u, "PRESS USER");

            /*
             * USER 버튼을 누르면
             * LEVEL 1부터 다시 시작
             */
            Memory_Wait_User_Button();

            Memory_Random_Seed();

            level = 1u;

            sequence[0] =
                Memory_Create_Input();

            continue;
        }


        /*
         * 16단계까지 전부 성공
         */
        if (level == MEMORY_MAX_LEVEL)
        {
            LCD_Print_Line(0u, "ALL 16 CLEAR!");
            LCD_Print_Line(1u, "PRESS RESET");

            Buzzer_Clear();

            for (;;)
            {
            }
        }


        /*
         * 현재 레벨 성공
         */
        Buzzer_Correct();

        snprintf(line,
                 sizeof(line),
                 "LEVEL %u CLEAR!",
                 level);

        LCD_Print_Line(0u, line);
        LCD_Print_Line(1u, "NEXT LEVEL...");

        TIM2_Delay(900u);


        /*
         * 기존 수열 뒤에 새 문제 하나 추가
         */
        sequence[level] =
            Memory_Create_Input();

        level++;
    }
}