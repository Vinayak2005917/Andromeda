<h1 align="center">
  <img src="frontend\assets\Logo.png"height="40" style="vertical-align: middle;">
Andromeda
</h1>

<div align="center">
    <a href="https://andromeda-teal.vercel.app/main.html">
        <img src="frontend/assets/Example_output_2.png" width="600">
    </a>
</div>


* A LMM's output does not need to a wall of text with a million bullet points. Markdown is a great way to format text, but it also has limits against the sheer amount of text some of these LLM's use to answer questions. 

* They also have an unprecidented ability to Code beautiful and interactive Web pages.


**So Andromeda is a Agent that can use the LLM's ability to code beautiful and interactive Web pages to answer questions in a more Visual and interactive way.**

The following are some screenshots of the output from Andromeda:

Prompt : ```Teach me about Orbital mechanics Visually!!```

Model : ```DeepSeek V4 Flash 0731```

<div align="center">
  <img src="frontend/assets/Example_output_1.png" width="800">
</div>

Compared to using a normal LLM that outputs a wall of text with a million bullet points, Andromeda can output a beautiful and interactive Web page that can be used to teach the user about Orbital mechanics visually.

# Tool and Features

1. **Get relevant webpages** - It uses the DuckDuckGo API to search the web for relevant webpages to answer the user's question.

2. **Batch read pages** - It can read multiple webpages for quries per webpage. It uses ```jira.ai```'s web page reader to read the webpages and extract relevant information from them using GPT 5 Nano.

3. **Search images** - It can search for images using the Serp API to find relevant images to answer the user's question.

4. **Update user** - It can provide progress updates for tasks requiring more than 2 tool calls.

5. **Send HTML response** - It sends a HTML along with a guess for long for the height of the iframe container of the HTML code. 

# Available Models

> Note : New LLM models are coming all the time so this list is volatile and will be updated as new models are released.

1. **GPT-5 Nano**
2. **DeepSeek V4 Flash 0731**
3. **GPT-OSS 120B**
4. **Qwen 3.5 Flash**
5. **Nemotron 3 Super 120B**
6. **Gemma 4 26b**
7. **Inception Mercury 2**

# Final Notes

- There are a few things i learnt making this project.
    1. Dynamic iframe height is a pain in the ass.
    2. Modern LLM's are suprisingly good at coding beautiful and interactive Web pages. (even more than i expected)
    3. Intent Classification is tricker than it looks. (i had to use a few tricks to get it to work properly)
    4. Generative UI UX will definitely be a thing in the future. (I can see myself using it quite often)
    5. Good image API's are hard to find. Serp API is very good and very limited.

- This project is part of a series of Agentic Projects that i am working on.
- Althouth i suspect not many will, you are full free to Contribute to this project. (i will be happy to accept any PR's).

## Thank you for checking out this project and i hope you find it useful.

<div align="center">
    <a href="https://andromeda-teal.vercel.app/index.html">
        <img src="frontend/assets/Landing_Page.png" width="600">
    </a>
</div>
