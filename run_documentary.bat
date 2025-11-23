@echo off
echo ========================================
echo   Chess Documentary - Cinematic Mode
echo ========================================
echo.
echo A visual journey through chess history
echo and artificial intelligence
echo.
echo Controls:
echo   SPACE   - Pause/Resume
echo   <- / -> - Adjust speed
echo   ESC / Q - Exit
echo.

python src/documentary.py %*

pause
