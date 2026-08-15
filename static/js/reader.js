let book = null;


document.addEventListener(
    "DOMContentLoaded",
    loadBook
);


async function loadBook() {

    const params =
        new URLSearchParams(
            window.location.search
        );


    const bookId =
        params.get("id");


    if (!bookId) {

        document.getElementById(
            "reader"
        ).innerHTML =
            "<p>No book selected.</p>";

        return;
    }


    const books =
        JSON.parse(
            localStorage.getItem(
                "library"
            ) || "[]"
        );


    book =
        books.find(
            item => item.id === bookId
        );


    if (!book) {

        document.getElementById(
            "reader"
        ).innerHTML =
            "<p>Book not found.</p>";

        return;
    }


    document.getElementById(
        "bookTitle"
    ).textContent =
        book.title;


    /*
     * Temporary reader.
     *
     * PDF.js / EPUB.js will replace
     * this section.
     */

    if (book.type === "pdf") {

        showPDF(book);

    } else if (book.type === "epub") {

        showEPUBMessage(book);

    }

}


function showPDF(book) {

    const reader =
        document.getElementById(
            "reader"
        );


    reader.innerHTML = `

        <iframe

            src="${book.link}"

            style="
                width:90%;
                height:90vh;
                border:0;
                background:white;
            ">

        </iframe>

    `;

}


function showEPUBMessage(book) {

    const reader =
        document.getElementById(
            "reader"
        );


    reader.innerHTML = `

        <div style="
            color:white;
            text-align:center;
            padding:50px;
        ">

            <h2>EPUB Reader</h2>

            <p>
                EPUB.js will be connected here.
            </p>

        </div>

    `;

}


function goBack() {

    window.location.href = "/";

}


function toggleDarkMode() {

    document.body.classList.toggle(
        "reader-dark"
    );

}


function toggleFullscreen() {

    if (!document.fullscreenElement) {

        document.documentElement
            .requestFullscreen();

    } else {

        document.exitFullscreen();

    }

}
