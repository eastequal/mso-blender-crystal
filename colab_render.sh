#!/bin/bash
# Colab T4 렌더 — 인자: SCENE START END SAMPLES  (예: bash colab_render.sh CRYSTAL2 1 450 32)
# 산출 = /content/out/<SCENE>/f%03d.png · 로그 = /content/render.log · 완료 판정은 «RENDERED 줄 수»로 한다(ls 개수 아님)
set -u
SCENE=${1:-CRYSTAL2}; A=${2:-1}; B=${3:-450}; S=${4:-32}
cd /content
apt-get -qq install -y libxi6 libxrender1 libxkbcommon0 libsm6 libgl1 libxxf86vm1 libxfixes3 >/dev/null 2>&1
if [ ! -x /content/blender/blender ]; then
  wget -q https://download.blender.org/release/Blender5.2/blender-5.2.2-linux-x64.tar.xz -O b.tar.xz
  tar xf b.tar.xz && mv blender-5.2.2-linux-x64 blender && rm -f b.tar.xz
fi
rm -rf pkg && git clone -q https://github.com/eastequal/mso-blender-crystal.git pkg
mkdir -p /content/out/$SCENE
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader > /content/gpu.txt 2>&1
cd /content/pkg
nohup /content/blender/blender -b -P render.py -- --scene "$SCENE" --frames "$A-$B" --samples "$S" \
  --out "/content/out/$SCENE" --flat --skip_existing --gpu > /content/render.log 2>&1 &
echo "LAUNCHED $SCENE $A-$B samples=$S pid=$!"
