document.addEventListener("DOMContentLoaded", function () {
  // Attach event listeners to forms
  function attachEventListeners() {
    document.querySelectorAll(".answer-form").forEach(function (form) {
      form.addEventListener("submit", submitForm);
    });
  }

  attachEventListeners(); // Call the function to attach initial event listeners

  async function submitForm(event) {
    event.preventDefault();
    event.stopPropagation();

    var form = event.target;

    // Disable the submit button and show loading state
    const submitButton = form.querySelector('input[type="submit"]');
    if (submitButton.disabled) {
      return false; // Exit if already processing
    }

    submitButton.disabled = true;
    submitButton.value = "Checking...";

    var formData = new FormData(form);
    var sectionIndex = form.getAttribute("data-section-index");

    formData.append("section_index", sectionIndex);

    try {
      const response = await fetch("/submit_answer", {
        method: "POST",
        body: formData,
        headers: {
          "X-CSRFToken": formData.get("csrf_token"),
        },
        credentials: "same-origin",
      });

      if (!response.ok) {
        throw new Error("Network response was not ok");
      }

      const data = await response.json();
      console.log("Data received from server:", data);

      // Replace the current section with the updated one from the server
      var sectionDiv = document.getElementById("section-" + data.section_index);
      var tempDiv = document.createElement("div");
      tempDiv.innerHTML = data.updated_section_html;
      var newSectionDiv = tempDiv.querySelector(".section");

      if (newSectionDiv) {
        // Remove any existing checkmarks before replacing
        const existingCheckmark =
          sectionDiv.querySelector(".success-checkmark");
        if (existingCheckmark) {
          existingCheckmark.remove();
        }

        sectionDiv.replaceWith(newSectionDiv);

        // If correct answer, ensure animation triggers
        if (data.feedback_type === "correct") {
          const feedbackElement = newSectionDiv.querySelector(".feedback");
          if (feedbackElement) {
            // Remove any existing checkmark first
            const existingCheckmark =
              feedbackElement.querySelector(".success-checkmark");
            if (existingCheckmark) {
              existingCheckmark.remove();
            }

            // Create and insert the new checkmark
            const checkmark = document.createElement("span");
            checkmark.className = "success-checkmark";
            checkmark.textContent = "✅";
            feedbackElement.insertBefore(checkmark, feedbackElement.firstChild);
          }
        }

        // Re-attach event listener to the new form
        var updatedForm = newSectionDiv.querySelector(".answer-form");
        if (updatedForm) {
          updatedForm.addEventListener("submit", submitForm);
        }

        // If the answer was correct, scroll to the feedback
        if (data.feedback_type === "correct") {
          const feedbackElement = newSectionDiv.querySelector(".feedback");
          if (feedbackElement) {
            feedbackElement.scrollIntoView({
              behavior: "smooth",
              block: "center",
            });
          }
        }

        // If there's a new section, append it (but check if it already exists)
        if (data.new_section_html && data.feedback_type === "correct") {
          console.log("Adding new section to the DOM.");
          var courseContent = document.getElementById("course-content");

          // Check if the next section already exists
          const nextSectionIndex = parseInt(sectionIndex) + 1;
          const nextSectionExists = document.getElementById(
            `section-${nextSectionIndex}`,
          );

          if (!nextSectionExists) {
            var tempDiv = document.createElement("div");
            tempDiv.innerHTML = data.new_section_html;
            var newSectionDiv = tempDiv.querySelector(".section");
            if (newSectionDiv) {
              courseContent.appendChild(newSectionDiv);

              // Attach event listener to the new form
              var newForm = newSectionDiv.querySelector(".answer-form");
              if (newForm) {
                newForm.addEventListener("submit", submitForm);
              }
            }
          }
        }
      } else {
        console.error("Could not find updated section HTML.");
      }

      // If course is completed, display the completion message
      if (data.completion_message) {
        console.log("Course completed, displaying completion message.");
        var courseContent = document.getElementById("course-content");
        // Remove any existing completion message
        const existingCompletion = courseContent.querySelector(
          ".completion-message",
        );
        if (existingCompletion) {
          existingCompletion.remove();
        }

        var tempDiv = document.createElement("div");
        tempDiv.innerHTML = data.completion_message;
        var completionDiv = tempDiv.querySelector(".completion-message");
        if (completionDiv) {
          courseContent.appendChild(completionDiv);
          completionDiv.scrollIntoView({ behavior: "smooth" });
        }
      }

      // Update the vertical progress bar
      if (data.progress_percentage !== undefined) {
        console.log("Updating progress bar:", data.progress_percentage);
        var progressFill = document.querySelector(".vertical-progress-fill");
        if (progressFill) {
          progressFill.style.height = data.progress_percentage + "%";
        }
      }
    } catch (error) {
      console.error("Error:", error);
    } finally {
      // Re-enable the submit button and restore original text
      submitButton.disabled = false;
      submitButton.value = "Check";
    }

    return false;
  }
});
