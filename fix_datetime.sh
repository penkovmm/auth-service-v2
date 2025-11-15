#!/bin/bash
# Fix datetime.utcnow() -> datetime.now(timezone.utc) across all files

cd /home/penkovmm/services/auth-service-v2

# List of files to fix
files=(
    "app/services/hh_oauth_service.py"
    "app/services/session_service.py"
    "app/services/admin_service.py"
    "app/api/routes/health.py"
    "app/db/repositories/audit.py"
    "app/db/repositories/token.py"
    "app/db/repositories/session.py"
    "app/db/repositories/user.py"
)

for file in "${files[@]}"; do
    echo "Fixing $file..."

    # Add timezone import if not present
    if ! grep -q "from datetime import.*timezone" "$file"; then
        # Check if there's a datetime import line
        if grep -q "^from datetime import" "$file"; then
            # Add timezone to existing import
            sed -i 's/^from datetime import \(.*\)$/from datetime import \1, timezone/' "$file"
        fi
    fi

    # Replace datetime.utcnow() with datetime.now(timezone.utc)
    sed -i 's/datetime\.utcnow()/datetime.now(timezone.utc)/g' "$file"
done

echo "All files fixed!"
