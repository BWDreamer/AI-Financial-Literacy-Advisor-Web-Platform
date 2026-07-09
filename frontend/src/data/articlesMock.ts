export type ArticleCategory = "Budgeting" | "Saving" | "Tax" | "Superannuation" | "Investing" | "Security";

export type ArticleContentBlock =
  | {
      type: "paragraph";
      text: string;
    }
  | {
      type: "image";
      src: string;
      alt: string;
      caption?: string;
    };

export type Article = {
  id: string;
  title: string;
  summary: string;
  coverImageUrl: string;
  authorName: string;
  sourceName: string;
  publishedAt: string;
  category: ArticleCategory;
  views: number;
  likes: number;
  saves: number;
  contentBlocks: ArticleContentBlock[];
};

export const articlesMock: Article[] = [
  {
    id: "budget-start",
    title: "How to Build a Budget That Survives Real Life",
    summary: "A simple guide to tracking income, planning spending and leaving room for irregular costs without feeling trapped by a spreadsheet.",
    coverImageUrl: "https://images.unsplash.com/photo-1554224155-6726b3ff858f?auto=format&fit=crop&w=900&q=80",
    authorName: "FinanceAI Learning Team",
    sourceName: "Knowledge Base Mock",
    publishedAt: "2026-07-02T09:30:00+10:00",
    category: "Budgeting",
    views: 1820,
    likes: 126,
    saves: 48,
    contentBlocks: [
      {
        type: "paragraph",
        text: "A useful budget starts with the money that actually arrives in your account and the spending that actually leaves it. Before setting a target, collect recent income, bills, subscriptions, groceries, transport costs and debt repayments.",
      },
      {
        type: "image",
        src: "https://images.unsplash.com/photo-1554224154-26032ffc0d07?auto=format&fit=crop&w=1200&q=80",
        alt: "A person reviewing household budget notes and receipts",
        caption: "Start with real spending records before setting a monthly target.",
      },
      {
        type: "paragraph",
        text: "Group your spending into needs, wants and savings. Needs are the costs required to keep daily life running. Wants are flexible lifestyle choices. Savings include emergency funds, short-term goals and longer-term wealth building.",
      },
      {
        type: "paragraph",
        text: "The best budget is not the strictest one. It is the one you can review and adjust every month. When your income changes or an unexpected cost appears, update the plan instead of abandoning it.",
      },
    ],
  },
  {
    id: "emergency-fund",
    title: "Emergency Funds: Why Cash Still Matters",
    summary: "Before investing or taking bigger risks, many households keep a cash buffer for rent, food, medical costs and sudden job changes.",
    coverImageUrl: "https://images.unsplash.com/photo-1579621970795-87facc2f976d?auto=format&fit=crop&w=900&q=80",
    authorName: "FinanceAI Learning Team",
    sourceName: "Knowledge Base Mock",
    publishedAt: "2026-06-28T14:00:00+10:00",
    category: "Saving",
    views: 1460,
    likes: 88,
    saves: 52,
    contentBlocks: [
      {
        type: "paragraph",
        text: "An emergency fund is money set aside for expenses that cannot easily wait. It can reduce the need to rely on credit cards, personal loans or rushed asset sales when something unexpected happens.",
      },
      {
        type: "paragraph",
        text: "There is no single perfect amount. A common learning benchmark is several months of essential expenses, but the right target depends on job stability, family responsibilities, rent or mortgage costs and access to support.",
      },
      {
        type: "image",
        src: "https://images.unsplash.com/photo-1607863680198-23d4b2565df0?auto=format&fit=crop&w=1200&q=80",
        alt: "Coins and notes saved in a clear jar",
        caption: "Emergency savings are designed for access and stability, not high returns.",
      },
      {
        type: "paragraph",
        text: "Keep this money somewhere accessible and low risk. The goal is not high return. The goal is having money available when timing matters.",
      },
    ],
  },
  {
    id: "compound-interest",
    title: "Compound Interest Without the Jargon",
    summary: "Understand how time, rate of return and regular contributions can change long-term savings outcomes.",
    coverImageUrl: "https://images.unsplash.com/photo-1520607162513-77705c0f0d4a?auto=format&fit=crop&w=900&q=80",
    authorName: "FinanceAI Learning Team",
    sourceName: "Knowledge Base Mock",
    publishedAt: "2026-06-20T10:00:00+10:00",
    category: "Saving",
    views: 2130,
    likes: 154,
    saves: 67,
    contentBlocks: [
      {
        type: "paragraph",
        text: "Compound interest means earning interest on both your original money and the interest already earned. Over long periods, this can make time one of the most important parts of a savings plan.",
      },
      {
        type: "image",
        src: "https://images.unsplash.com/photo-1551288049-bebda4e38f71?auto=format&fit=crop&w=1200&q=80",
        alt: "A financial chart showing growth over time",
        caption: "Compound growth is easiest to understand when you compare different time horizons.",
      },
      {
        type: "paragraph",
        text: "Three inputs matter most: the starting balance, the regular contribution and the growth rate. Small changes in contribution habits can become meaningful when repeated for years.",
      },
      {
        type: "paragraph",
        text: "Calculators are useful because they let you test scenarios before making commitments. Treat the result as an estimate, not a guarantee.",
      },
    ],
  },
  {
    id: "marginal-tax",
    title: "Marginal Tax Rates: What They Actually Mean",
    summary: "Only part of your income is taxed at each bracket rate. This article explains the idea with plain-language examples.",
    coverImageUrl: "https://images.unsplash.com/photo-1450101499163-c8848c66ca85?auto=format&fit=crop&w=900&q=80",
    authorName: "FinanceAI Learning Team",
    sourceName: "Knowledge Base Mock",
    publishedAt: "2026-06-16T16:45:00+10:00",
    category: "Tax",
    views: 1210,
    likes: 97,
    saves: 34,
    contentBlocks: [
      {
        type: "paragraph",
        text: "A marginal tax system does not usually apply one rate to all of your income. Instead, income is divided into layers, and each layer has its own rate.",
      },
      {
        type: "paragraph",
        text: "This matters because earning extra income does not mean your whole income suddenly moves to a higher tax rate. Only the income inside the higher bracket is affected.",
      },
      {
        type: "image",
        src: "https://images.unsplash.com/photo-1554224155-8d04cb21cd6c?auto=format&fit=crop&w=1200&q=80",
        alt: "Tax forms and a calculator on a desk",
        caption: "Tax brackets are easier to understand as layers rather than one rate applied to everything.",
      },
      {
        type: "paragraph",
        text: "Tax rules can change by year and personal situation. Use official sources or professional advice for decisions, and use learning tools to understand the general concept.",
      },
    ],
  },
  {
    id: "super-basics",
    title: "Superannuation Basics for New Workers",
    summary: "A beginner-friendly explanation of employer contributions, long-term retirement savings and why fees matter.",
    coverImageUrl: "https://images.unsplash.com/photo-1565514020179-026b92b84bb6?auto=format&fit=crop&w=900&q=80",
    authorName: "FinanceAI Learning Team",
    sourceName: "Knowledge Base Mock",
    publishedAt: "2026-06-08T13:10:00+10:00",
    category: "Superannuation",
    views: 980,
    likes: 76,
    saves: 29,
    contentBlocks: [
      {
        type: "paragraph",
        text: "Superannuation is designed to help people save for retirement during their working life. For many employees in Australia, employers make regular contributions into a super fund.",
      },
      {
        type: "image",
        src: "https://images.unsplash.com/photo-1573496130141-209d200cebd8?auto=format&fit=crop&w=1200&q=80",
        alt: "A worker reviewing long-term financial paperwork",
        caption: "Superannuation is long-term money, so small settings can matter over time.",
      },
      {
        type: "paragraph",
        text: "Because super is long term, small differences in fees, insurance settings and investment options may matter over time. It is worth understanding the basics even when retirement feels far away.",
      },
      {
        type: "paragraph",
        text: "This article is educational only. Super rules and contribution settings can change, so check current official information before making decisions.",
      },
    ],
  },
  {
    id: "investment-risk",
    title: "Risk and Diversification When You Start Investing",
    summary: "Shares, bonds, cash and property behave differently. Diversification helps avoid relying on a single outcome.",
    coverImageUrl: "https://images.unsplash.com/photo-1642543492481-44e81e3914a7?auto=format&fit=crop&w=900&q=80",
    authorName: "FinanceAI Learning Team",
    sourceName: "Knowledge Base Mock",
    publishedAt: "2026-05-30T12:30:00+10:00",
    category: "Investing",
    views: 2450,
    likes: 201,
    saves: 94,
    contentBlocks: [
      {
        type: "paragraph",
        text: "Investment risk means the outcome may be different from what you expect. Some assets can rise and fall quickly, while others may be more stable but grow more slowly.",
      },
      {
        type: "image",
        src: "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?auto=format&fit=crop&w=1200&q=80",
        alt: "Investment market charts on a screen",
        caption: "Different assets can move in different ways, which is why diversification is an important learning topic.",
      },
      {
        type: "paragraph",
        text: "Diversification means spreading exposure across different assets, industries or regions. It does not remove risk, but it can reduce the effect of one poor outcome.",
      },
      {
        type: "paragraph",
        text: "Before investing, understand your time frame, emergency fund and ability to handle losses. Learning the language of risk is a first step, not a recommendation to buy anything.",
      },
    ],
  },
  {
    id: "scam-safety",
    title: "How to Spot Common Financial Scam Signals",
    summary: "Pressure, secrecy and guaranteed returns are warning signs. Learn what to pause and check before sending money.",
    coverImageUrl: "https://images.unsplash.com/photo-1563986768609-322da13575f3?auto=format&fit=crop&w=900&q=80",
    authorName: "FinanceAI Learning Team",
    sourceName: "Knowledge Base Mock",
    publishedAt: "2026-05-21T15:20:00+10:00",
    category: "Security",
    views: 1675,
    likes: 132,
    saves: 58,
    contentBlocks: [
      {
        type: "paragraph",
        text: "Financial scams often create urgency. A message may say an account will close, an opportunity will disappear or a payment must be made immediately.",
      },
      {
        type: "paragraph",
        text: "Be careful with promises of guaranteed high returns, requests for remote access, or instructions to keep the conversation secret. These are strong reasons to stop and verify independently.",
      },
      {
        type: "image",
        src: "https://images.unsplash.com/photo-1614064641938-3bbee52942c7?auto=format&fit=crop&w=1200&q=80",
        alt: "A phone and laptop showing online security concepts",
        caption: "Pause before clicking links, sharing codes or sending money under pressure.",
      },
      {
        type: "paragraph",
        text: "If something feels suspicious, do not click links or share codes. Use official websites, trusted phone numbers and independent advice channels.",
      },
    ],
  },
];

export function findArticleById(articleId: string | undefined) {
  return articlesMock.find((article) => article.id === articleId);
}
