## Validation Procedure

After merging the Pull Request into `main`, validate the implementation locally before creating a new release.

### 1. Update the local development clone

```bash
cd /config/dev/bticino-classe100x-ha

git pull
```

### 2. Replace the installed integration

```bash
cd /config

rm -rf custom_components/bticino_classe100x

cp -r \
/config/dev/bticino-classe100x-ha/custom_components/bticino_classe100x \
/config/custom_components/
```

### 3. Restart Home Assistant

```bash
ha core restart
```

### 4. Verify the expected code is installed

Use one or more `grep` commands that uniquely identify the merged feature.

Examples:

```bash
grep -Rni "BINARY_SENSOR_DESCRIPTIONS" \
/config/custom_components/bticino_classe100x
```

or

```bash
grep -Rni "async_update_device_registry" \
/config/custom_components/bticino_classe100x
```

### 5. Run the Health Check

```bash
python3 \
/config/dev/bticino-classe100x-ha/tools/diagnostics/health_check.py \
--config /config
```

Expected:

```
OVERALL STATUS: PASS
```

### 6. Check Home Assistant logs

```bash
ha core logs -n 300 | grep -Ei \
"custom_components.bticino_classe100x|bticino_classe100x|exception|error"
```

Only the standard Home Assistant warning about custom integrations should appear.

### 7. Validate the feature manually

Verify the functionality introduced by this Pull Request using the Home Assistant UI.

Only after successful validation should a version bump and GitHub Release be created.
