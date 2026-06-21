export interface ProvinceData {
  id: string;
  name: string;
  markets: string[];
}

export const PROVINCES: ProvinceData[] = [
  {
    id: 'luanda',
    name: 'Luanda',
    markets: ['Mercado Roque Santeiro', 'Mercado do Kikolo', 'Mercado do Asa', 'Mercado 1º de Maio', 'Mercado Kinaxixi', 'Feira do Benfica'],
  },
  {
    id: 'huambo',
    name: 'Huambo',
    markets: ['Mercado Central do Huambo', 'Feira de Caála', 'Mercado do Tchivinguiro'],
  },
  {
    id: 'bie',
    name: 'Bié',
    markets: ['Mercado do Cuíto', 'Mercado de Camacupa', 'Feira do Chinguar'],
  },
  {
    id: 'malanje',
    name: 'Malanje',
    markets: ['Mercado Central de Malanje', 'Feira de Cacuso'],
  },
  {
    id: 'lunda-norte',
    name: 'Lunda Norte',
    markets: ['Mercado de Dundo', 'Feira de Lucapa'],
  },
  {
    id: 'lunda-sul',
    name: 'Lunda Sul',
    markets: ['Mercado de Saurimo', 'Feira de Muconda'],
  },
  {
    id: 'moxico',
    name: 'Moxico',
    markets: ['Mercado do Luena', 'Feira do Léua'],
  },
  {
    id: 'cuando-cubango',
    name: 'Cuando Cubango',
    markets: ['Mercado do Menongue', 'Feira de Cuito Cuanavale'],
  },
  {
    id: 'namibe',
    name: 'Namibe',
    markets: ['Mercado Central do Namibe', 'Porto do Namibe', 'Feira de Tombwa'],
  },
  {
    id: 'cunene',
    name: 'Cunene',
    markets: ['Mercado do Ondjiva', 'Feira de Xangongo'],
  },
  {
    id: 'huila',
    name: 'Huíla',
    markets: ['Mercado Central do Lubango', 'Feira de Tchiombe', 'Mercado de Matala'],
  },
  {
    id: 'benguela',
    name: 'Benguela',
    markets: ['Mercado Central de Benguela', 'Porto do Lobito', 'Feira do Cubal'],
  },
  {
    id: 'kwanza-sul',
    name: 'Kwanza Sul',
    markets: ['Mercado do Sumbe', 'Feira do Porto Amboim', 'Mercado de Waku-Kungo'],
  },
  {
    id: 'kwanza-norte',
    name: 'Kwanza Norte',
    markets: ["Mercado de N'dalatando", 'Feira de Lucala'],
  },
  {
    id: 'bengo',
    name: 'Bengo',
    markets: ['Mercado de Caxito', 'Feira de Bula Atumba'],
  },
  {
    id: 'uige',
    name: 'Uíge',
    markets: ['Mercado Central do Uíge', 'Feira de Negage'],
  },
  {
    id: 'zaire',
    name: 'Zaire',
    markets: ["Mercado de M'banza Kongo", 'Feira de Soyo'],
  },
  {
    id: 'cabinda',
    name: 'Cabinda',
    markets: ['Mercado Central de Cabinda', 'Feira de Belize'],
  },
];
