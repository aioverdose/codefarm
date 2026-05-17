@echo off
setlocal EnableExtensions

set "CODEFARM_ROOT=G:\codefarm"
if exist "%CODEFARM_ROOT%\tools\env.bat" call "%CODEFARM_ROOT%\tools\env.bat"

"%PYTHON_EXE%" "%CODEFARM_ROOT%\observatory\metrics-collector.py"
"%PYTHON_EXE%" "%CODEFARM_ROOT%\observatory\ui-generator.py" >nul

echo.
echo UI: %CODEFARM_ROOT%\observatory\ui\index.html
echo.
echo State snapshot:
"%PYTHON_EXE%" -c "import json; from pathlib import Path; root=Path('G:/codefarm'); s=json.load(open(root/'state.json')); orgs=s.get('organisms',{}); active=[k for k in orgs if (root/'organisms'/k/'metabolism.py').exists()]; observed=[k for k in orgs if k not in active]; pool=s.get('nutrient_pool',{}); metrics=s.get('metrics',{}); print('Status: {}'.format('alive' if active else 'empty')); print('Population active: {}'.format(len(active))); print('Organisms: {}'.format(', '.join(active))); print('Observed artifacts: {}'.format(', '.join(observed) if observed else 'none')); print('Pool calories: {}'.format(pool.get('available_calories',0))); print('Lifetime nutrients: {}'.format(metrics.get('lifetime_nutrients',0))); print('Deaths 24h: {}'.format(metrics.get('deaths_24h',0)))"

echo.
echo Latest CodeFarm log:
"%PYTHON_EXE%" -c "from pathlib import Path; p=Path('G:/codefarm/logs'); logs=sorted(p.glob('codefarm-*.log')); lines=logs[-1].read_text(encoding='utf-8').splitlines()[-10:] if logs else []; print('\n'.join(lines) if lines else 'No logs found.')"

endlocal
