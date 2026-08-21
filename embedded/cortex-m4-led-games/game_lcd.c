#include "device_driver.h"
#include <stdio.h>

#define LCD_LINE_LENGTH  16u

static void Game_LCD_Clear_Line(unsigned int row)
{
    LCD_Set_Cursor(row, 0u);
    LCD_Print("                ");
}

/*
 * 게임 시작 대기 화면
 */
void Game_LCD_Show_Start(void)
{
    LCD_Clear();

    LCD_Set_Cursor(0u, 0u);
    LCD_Print("REACTION GAME");

    LCD_Set_Cursor(1u, 0u);
    LCD_Print("PRESS USER BTN");
}

/*
 * 라운드 시작 전 대기 화면
 */
void Game_LCD_Show_Wait(unsigned int round,
                        unsigned int total_round,
                        unsigned int limit_ms)
{
    char line[17];

    LCD_Clear();

    snprintf(line,
             sizeof(line),
             "ROUND %02u/%02u",
             round,
             total_round);

    LCD_Set_Cursor(0u, 0u);
    LCD_Print(line);

    snprintf(line,
             sizeof(line),
             "LIMIT %4u ms",
             limit_ms);

    LCD_Set_Cursor(1u, 0u);
    LCD_Print(line);
}

/*
 * LED가 켜졌을 때 GO 화면
 */
void Game_LCD_Show_Go(unsigned int target_led,
                      unsigned int target_button)
{
    char line[17];

    LCD_Clear();

    LCD_Set_Cursor(0u, 0u);
    LCD_Print("GO!");

    snprintf(line,
             sizeof(line),
             "LED%u -> BTN%u",
             target_led,
             target_button);

    LCD_Set_Cursor(1u, 0u);
    LCD_Print(line);
}

/*
 * 정답 화면
 */
void Game_LCD_Show_Correct(unsigned int reaction_ms)
{
    char line[17];

    LCD_Clear();

    LCD_Set_Cursor(0u, 0u);
    LCD_Print("CORRECT!");

    snprintf(line,
             sizeof(line),
             "TIME %4u ms",
             reaction_ms);

    LCD_Set_Cursor(1u, 0u);
    LCD_Print(line);
}

/*
 * 오답 화면
 */
void Game_LCD_Show_Wrong(unsigned int pressed_button,
                         unsigned int correct_button)
{
    char line[17];

    LCD_Clear();

    LCD_Set_Cursor(0u, 0u);
    LCD_Print("WRONG BUTTON!");

    snprintf(line,
             sizeof(line),
             "BTN%u -> BTN%u",
             pressed_button,
             correct_button);

    LCD_Set_Cursor(1u, 0u);
    LCD_Print(line);
}

/*
 * 시간 초과 화면
 */
void Game_LCD_Show_Timeout(unsigned int limit_ms)
{
    char line[17];

    LCD_Clear();

    LCD_Set_Cursor(0u, 0u);
    LCD_Print("TIME OUT!");

    snprintf(line,
             sizeof(line),
             "LIMIT %4u ms",
             limit_ms);

    LCD_Set_Cursor(1u, 0u);
    LCD_Print(line);
}

/*
 * 너무 일찍 버튼을 누른 경우
 */
void Game_LCD_Show_Early(void)
{
    LCD_Clear();

    LCD_Set_Cursor(0u, 0u);
    LCD_Print("TOO EARLY!");

    LCD_Set_Cursor(1u, 0u);
    LCD_Print("GAME OVER");
}

/*
 * 모든 라운드 성공
 */
void Game_LCD_Show_Clear(unsigned int average_ms)
{
    (void)average_ms;

    LCD_Clear();

    LCD_Set_Cursor(0u, 0u);
    LCD_Print("ALL 10 CLEAR!");

    LCD_Set_Cursor(1u, 0u);
    LCD_Print("CONGRATULATIONS");
}

/*
 * 중간에 게임 종료
 */
void Game_LCD_Show_Game_Over(unsigned int round)
{
    char line[17];

    LCD_Clear();

    LCD_Set_Cursor(0u, 0u);
    LCD_Print("GAME OVER");

    snprintf(line,
             sizeof(line),
             "ROUND %u",
             round);

    LCD_Set_Cursor(1u, 0u);
    LCD_Print(line);
}