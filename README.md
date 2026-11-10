# Living Memory · MiniMax H3 Batch for ComfyUI / Vast.ai

Пакетная обработка **фотография + индивидуальный TXT-промпт → отдельное MP4 со звуком**. Основа — [официальный MiniMax H3 I2V workflow](https://github.com/Comfy-Org/workflow_templates/blob/main/templates/video_minimax_h3_i2v.json), **не переизобретённая видеомодель**. Сохраняются официальная H3 subgraph, выбор моделей, звук, длительность, размеры, turbo-настройки. Изменяются только загрузчики, связь текста с `prompt`, очередь и имя выходного видео.

> **Статус**: генератор и графовые тесты проверены локально на структурном фикстуре. Реальная генерация на Vast.ai и поведение frontend-плагина под GPU пока не проверены. Первым запуском сделайте тест на 2 фотографиях.

## Как работает

```
/workspace/living_memory/input/
  photo_001.jpg
  photo_001.txt     # английский H3 video+audio prompt
  photo_002.png
  photo_002.txt
  photo_003.webp
  photo_003.txt
```

`FolderBatch Sync Queue` сопоставляет файлы **By Name**, выбирает одну пару на запуск и автоматически передаёт следующую пару в очередь. Каждый `TXT` — весь промпт одной сцены, без негативного промпта. `FolderBatch Load Image` подключён к `first_frame`, `FolderBatch Load Text` — к `prompt` официального H3 subgraph. `SaveVideo` принимает исходное имя фото через `filename_prefix`, формат **mp4**, кодек `auto`. Примеры: `photo_001_00001.mp4`, `photo_002_00001.mp4` в `ComfyUI/output/` (суффиксы зависят от счётчиков ComfyUI).

**Важно:** в папке должны быть только пары с одинаковым именем, кроме расширения. `missing_policy=Error` останавливает выполнение при отсутствующей паре, не подменяя её чужим промптом. По умолчанию изображения обрабатываются по имени A–Z.

## Один раз: загрузить в GitHub

**Создайте новый пустой репозиторий** (например `living-memory-h3-batch`). Это не настоящий fork исходного гигантского `workflow_templates`: здесь хранятся только ваши изменения + автоматически собираемый JSON.

Распакуйте архив, затем из корня папки:

```bash
git init
git branch -M main
git add .
git commit -m "Add Living Memory H3 batch"
git remote add origin https://github.com/<YOUR_USERNAME>/living-memory-h3-batch.git
git push -u origin main
```

GitHub Actions автоматически скачает полный официальный workflow и **создаст `workflows/video_minimax_h3_i2v_batch.json` прямо в вашем репозитории**. Проверьте вкладку **Actions**. Если при коммите workflow появится ошибка `403`, откройте **Settings → Actions → General → Workflow permissions → Read and write permissions** и повторите workflow через **Run workflow**. Если ветка защищена от коммитов, используйте локальную сборку ниже.

До первого запуска GitHub Actions JSON ещё не существует: он **генерируется** из полной актуальной официальной схемы, потому что копировать большой upstream JSON в исходный репозиторий необязательно.

Локальная сборка по тому же принципу:

```bash
python3 scripts/test_build_workflow.py
python3 scripts/build_workflow.py
```

## Запуск нового инстанса Vast.ai

После успешного Action на вашем Mac с установленным `vastai` CLI:

```bash
bash scripts/create_vast_instance.sh <OFFER_ID> <YOUR_USERNAME>/living-memory-h3-batch
```

Скрипт повторяет ваши опции `vastai/comfy:v0.35.0-cuda-13.2-py312`, `COMFYUI_ARGS`, порты и `--disk 65 --jupyter --ssh --direct`. Вместо обычного I2V скачивает **ваш подготовленный batch JSON**, при этом оставляет исходные R2V/T2V и устанавливает [ComfyUI-FolderBatch](https://github.com/aiai-r/ComfyUI-FolderBatch). В исходном CLI были демо-фото: здесь они удалены, потому что нужны ваши фотографии. При нехватке диска увеличьте `--disk` или уберите ненужные R2V/T2V шаблоны.

Когда Vast.ai будет готов: загрузите пары `.jpg/.png/.webp + .txt` в `/workspace/living_memory/input` через Jupyter/Syncthing; откройте `video_minimax_h3_i2v_batch` в меню Workflows ComfyUI; проверьте значения длительности и разрешения; нажмите **Queue Prompt** один раз. Для первого теста оставьте вкладку ComfyUI открытой: автоматическая постановка следующих заданий реализуется frontend-расширением FolderBatch.

## Если инстанс уже запущен

Скопируйте/клонируйте **этот** репозиторий на Vast.ai (например в `/workspace/living-memory-h3-batch`) и запустите:

```bash
cd /workspace/living-memory-h3-batch
bash scripts/install_existing_vast.sh
```

Скрипт установит расширение и сгенерирует **полный** batch JSON из официального шаблона непосредственно в `ComfyUI/user/default/workflows`. Перезапустите ComfyUI, чтобы он подхватил ноды. Не запускайте повторную загрузку многогигабайтных моделей, если они уже есть.

## Где менять настройки

- `FolderBatch Sync Queue → common_folder` — общая папка, по умолчанию `/workspace/living_memory/input`.
- `start_at` — индекс первого фото (0 = первое). Можно продолжить с нужного индекса.
- `auto_queue = true` — автоматический переход к следующему фото.
- `sync_mode = By Name`, `missing_policy = Error` — строгое сопоставление.
- `H3 subgraph` — длительность, разрешение, звук и turbo работают как в официальном шаблоне; **никаких жёстко заданных 8 секунд**.
- `SaveVideo` — формат mp4, имена от `base_name`.

## Ограничения

1. Это ComfyUI **UI workflow** с subgraph, **не** готовый API-format JSON для `/prompt` без преобразования фронтендом ComfyUI.
2. Без запуска реальной Vast.ai GPU-среды нельзя гарантировать совместимость конкретной версии H3 и FolderBatch; тестируйте на 2 фотографиях перед длинной очередью.
3. Автоочередь зависит от frontend-плагина; браузер ComfyUI лучше не закрывать до завершения. Отдельного серверного фонового демона в этом пакете нет.
4. Обновления официального шаблона могут изменить структуру subgraph. Тогда скрипт выдаст явную ошибку, а не тихо подключит промпт не туда.
5. Содержимое ваших фотографий и TXT **не отправляется в GitHub**. Храните их только на вашем Vast.ai или другом закрытом хранилище.

## Ссылки

- [Comfy-Org original I2V template](https://raw.githubusercontent.com/Comfy-Org/workflow_templates/refs/heads/main/templates/video_minimax_h3_i2v.json)
- [FolderBatch node sources and README](https://github.com/aiai-r/ComfyUI-FolderBatch)
- [Vast.ai provisioning documentation](https://github.com/vast-ai/base-image/blob/main/ROOT/opt/instance-tools/lib/provisioner/README.md)

Технически все файлы этого репозитория можно редактировать, форкать и вести под своим GitHub-аккаунтом. Исходные проекты сохраняют собственные лицензии.
