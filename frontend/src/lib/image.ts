/** Reduz e comprime a foto NO NAVEGADOR: o maior lado fica com no máximo `maxSide` px (sem esticar nem ampliar) e sai
 *  como JPEG. O backend gera depois o tamanho exato de cada modelo (ESP32 e servidor), que são configuráveis. */
export async function prepareImage(file: Blob, maxSide: number, quality: number): Promise<Blob> {
  const bmp = await createImageBitmap(file, { imageOrientation: "from-image" }).catch(() => {
    throw new Error("Não consegui abrir essa imagem. Use JPEG, PNG ou WEBP.");
  });
  const scale = Math.min(1, maxSide / Math.max(bmp.width, bmp.height));
  const w = Math.max(1, Math.round(bmp.width * scale));
  const h = Math.max(1, Math.round(bmp.height * scale));
  const canvas = document.createElement("canvas");
  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("Seu navegador não conseguiu preparar a imagem.");
  ctx.imageSmoothingQuality = "high";
  ctx.drawImage(bmp, 0, 0, w, h);
  bmp.close();
  return new Promise((resolve, reject) =>
    canvas.toBlob((b) => (b ? resolve(b) : reject(new Error("Falha ao comprimir a imagem."))), "image/jpeg", quality / 100),
  );
}
