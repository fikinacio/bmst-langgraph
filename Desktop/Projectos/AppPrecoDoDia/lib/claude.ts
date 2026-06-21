import type { ExtractedPrice, ExtractError } from './types';

// ⚠️ SUBSTITUIR pelo conteúdo do PROMPT 6 quando disponível
const SYSTEM_PROMPT = `Você é um assistente especializado em extração de dados de preços de mercado em Angola.
Quando o utilizador descrever um preço, extraia as informações estruturadas.
Responda SEMPRE em JSON válido com exactamente esta estrutura:
{ "product": string, "price": number, "unit": string, "currency": "AOA" | "USD", "confidence": number }
- "confidence" é de 0 a 1 (1 = certeza total)
- "currency" é "AOA" (Kwanza) por defeito, "USD" se explicitamente mencionado
- "unit" exemplos: "kg", "saco 25kg", "litro", "caixa", "unidade"
Se não conseguir extrair com confiança mínima de 0.6, retorne: { "error": "motivo" }`;

export async function extractPriceFromText(
  text: string,
  province: string
): Promise<ExtractedPrice> {
  const apiKey = process.env.EXPO_PUBLIC_CLAUDE_API_KEY;
  if (!apiKey) throw new Error('EXPO_PUBLIC_CLAUDE_API_KEY não configurada');

  const response = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': apiKey,
      'anthropic-version': '2023-06-01',
    },
    body: JSON.stringify({
      model: 'claude-sonnet-4-6',
      max_tokens: 256,
      system: SYSTEM_PROMPT,
      messages: [
        {
          role: 'user',
          content: `Província: ${province}\n\nTexto do utilizador: ${text}`,
        },
      ],
    }),
  });

  if (!response.ok) {
    throw new Error(`Claude API erro ${response.status}: ${await response.text()}`);
  }

  const data = await response.json();
  const content = data.content[0]?.text;

  if (!content) throw new Error('Resposta vazia da Claude API');

  const parsed: ExtractedPrice | ExtractError = JSON.parse(content);

  if ('error' in parsed) {
    throw new Error(`Extracção falhou: ${parsed.error}`);
  }

  return parsed;
}
