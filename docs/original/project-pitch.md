# Project Pitch

Podcasts have become a hugely popular news source—almost one-third of US adults regularly tune in for news, and many listeners trust podcasts even more than traditional media. But unlike traditional news, podcasts have practically no moderation or fact-checking, so misinformation can easily spread unchecked, with notable podcasters like Joe Rogan and Alex Jones highlighting this risk. Despite podcasts being publicly available and easy to analyze using transcription and LLMs, surprisingly little research has looked into how misinformation circulates through this medium. I propose to fill that gap by investigating how widespread misinformation is in podcasts, identifying the podcasts and topics most involved, and figuring out the best ways to automatically detect misinformation in long-form audio. Additionally, we can explore its relationship to monetization, how misinformation spreads between podcasts, and many more important questions.

## Why podcasts?

**Podcasts are a very popular news source**

- 67% of Americans have listened to a podcast, 42% listen every month, 34% listen every week (https://www.edisonresearch.com/podcast-listening-hits-record-highs/)
- 27% (34% for 18-49yo) of US adults get news often or sometimes from podcasts (https://www.pewresearch.org/journalism/fact-sheet/news-platform-fact-sheet/)
- 88% of US podcast listeners say they listen to podcasts to learn, 64% for news (https://www.pewresearch.org/journalism/2023/04/18/podcasts-as-a-source-of-news-and-information/)
- 88% of US podcasts listeners say they think news on podcasts is mostly accurate, 31% say they trust podcasts for news more than other sources (https://www.pewresearch.org/journalism/2023/04/18/podcasts-as-a-source-of-news-and-information/)
- 46% of republican podcast listeners say they trust news from podcasts more than other sources, 81% say they hear news from podcasts that they wouldn’t have heard elsewhere (https://www.pewresearch.org/journalism/2023/04/18/podcasts-as-a-source-of-news-and-information/)

**Podcasts are not moderated or fact-checked**

- Anyone can publish a podcast, there’s no barrier to entry
- Many (most?) podcasts that have some news component are not affiliated with a news organization that does fact checking
- There’s no accountability
- Podcasts don’t rely on a centralized platform, so cannot be taken down
- Most podcast discovery apps don’t do much, if any, moderation, especially based on misinformation content
- Very high-profile examples of misinformation spread via podcasts, including Joe Rogan and Alex Jones

**Podcast data is easy to collect and analyze**

- Podcasts are shared publicly via RSS, so anyone can download the audio easily
- Speech-to-text models are very good at transcribing high-quality audio like podcasts
- We can use LLMs to break down podcasts into individual claims

**There is no existing literature studying podcasts as a source of misinformation**

- We really don’t know how much misinformation is spread via podcasts
- My hypothesis is that it’s a lot, and the misinformation that is shared via podcasts is more sticky than misinformation shared on social media (because there’s more trust)
- There’s no published work on analyzing podcasts for misinformation
    - One article on the subject that would be a good starting point: https://www.brookings.edu/articles/audible-reckoning-how-top-political-podcasters-spread-unsubstantiated-and-false-claims/
    - One paper creates a small dataset, but doesn’t analyze: https://arxiv.org/html/2502.01402

## Proposed Research Questions

- How much misinformation is spread via podcasts?
- What misinformation topics are spread most via podcasts?
- Which podcasts spread the most misinformation?
- What’s the best way to automatically detect misinformation in long-form content like podcasts?
    - Train classifier model
    - LLM zero-shot/few-shot/fine-tuned
    - LLM with RAG, search, etc
    - LLM with CoT reasoning
- How accurate can we make a claim-level misinformation detector for podcasts?
- Can we categorize types or levels of misinformation?
- Does some misinformation appear to originate on podcasts?
    - Are there news stories, social media posts, etc that come first?
- Does monetization (advertising, youtube, spotify) influence the prevalence or type of misinformation spread via podcasts?
- Are there any factors that predict the likelihood that a podcast contains some misinformation (eg publisher, ratings, episode frequency, category, etc)?
- Are there super-spreader podcasts, or do most tend to mention misinformation only occasionally?
- Can we identify new misinformation topics before they become mainstream?
- Can we find communities of podcasts that discuss similar misinformation at similar times?
- Is misinformation mentioned more by podcasts hosts or guests?
- How quickly do new or trending misinformation topics arise in the podcast ecosystem?
- How often do false claims from “fringe” podcasts get amplified by more mainstream podcasts?
- How do hosts or guests introduce misinformation (e.g., disclaimers, qualifiers) or attempt to legitimize it?
- Do podcasters mention sources when introducing misinformation?
- Which specific individuals (hosts/guests) appear most frequently in episodes containing recurring misinformation narratives?

## Relevant Links

- https://www.pewresearch.org/journalism/2023/04/18/podcasts-as-a-source-of-news-and-information/
- https://www.brookings.edu/articles/the-challenge-of-detecting-misinformation-in-podcasting/
- https://www.brookings.edu/articles/audible-reckoning-how-top-political-podcasters-spread-unsubstantiated-and-false-claims/
- https://arxiv.org/html/2502.01402
- https://aclanthology.org/2020.coling-main.519/
- https://podcastsdataset.byspotify.com/
