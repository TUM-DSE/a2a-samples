#include <assert.h>
#include <fcntl.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>
#include <atomic>
#include <algorithm>
#include <sys/io.h>
#include <errno.h>

#include "include/args_client.h"
#include "include/shm.h"

#define MIN(a, b) (((a) < (b)) ? (a) : (b))
#define MAX(a, b) (((a) > (b)) ? (a) : (b))

static std::atomic<int> id = 0;

static Communication comm;

void write_to_shm(struct SharedMemory* shm, const char* text, int n_tokens_to_gen, int index,
                  int prio, enum Lora lora, float throughput, int outb_id) {
    // TODO: this zero set is a safety net
    // currently it protects the memory if a client dies without cleaning the memory
    // A better way would be register a cleaner signal handler.
    for (int i = 0; i < MAX_TEXT; i++) {
        shm->requests[index].text[i] = 0;
    }

    //printf("Writing to shm index: [%d]\n"
    //       "-> Current string in cell [%d] (should be empty): %s\n"
    //       "-> Writing to cell...\n",
    //       index, index, shm->requests[index].text);

	// TODO: strcpy
    for (int i = 0; i < (int)strlen(text); i++) {
        shm->requests[index].text[i] = text[i];
    }

    //printf("-> Resulting string in cell: %s\n", shm->requests[index].text);

    shm->requests[index].n_chars_to_gen = n_tokens_to_gen;
    shm->requests[index].id = id++;
    shm->requests[index].prio = prio;
    shm->requests[index].lora = lora;
    shm->requests[index].throughput = throughput;
	shm->requests[index].outb_id = outb_id;
}

std::string get_result(struct Communication* comm, int str_len, int n_gen, int free_request_slot) {
	SharedMemory* shm = (SharedMemory*)comm->requestQueue;

	std::string result = "";
	sem_wait(&shm->requests[free_request_slot].clientNotifier);
	result.append("{\"text\": \" ");
	std::string s = shm->requests[free_request_slot].text;
	std::replace(s.begin(), s.end(), '\"', ' ');
	std::replace(s.begin(), s.end(), '\\', ' ');
	result.append(s);
	result.append("\", \"timings\": {");

	result.append("\"tokens_per_second\": \"");
	result.append(std::to_string(shm->requests[free_request_slot].tokens_per_second));
	result.append("\"");
	result.append(", ");

	result.append("\"decode_latency_ms\": \"");
	result.append(std::to_string(shm->requests[free_request_slot].decode_time_ms));
	result.append("\"");
	result.append(", ");

	result.append("\"scheduling_delay_ms\": \"");
	result.append(std::to_string(shm->requests[free_request_slot].scheduling_time_ms));
	result.append("\"");
	result.append(", ");

	result.append("\"kv_cache_util\": \"");
	result.append(std::to_string(shm->requests[free_request_slot].kv_cache_util));
	result.append("\"");

	result.append("}}");


	// TODO: Do I need this busy loop?
    //printf("\nRequest has been fully answered!\n");
	return result;
}

int find_free_shm_request(struct Communication* comm) {
	SharedMemory* shm = (SharedMemory*)comm->requestQueue;
	//printf("LOOKING FOR FREE SPOT!\n");
    for (int i = 0; i < MAX_REQUESTS; i++) {
//		printf("Taking mutex lock: %p\n",&(shm->requests[i].mutex));
//		printf("Got mutex lock!!\n");
        if (pthread_mutex_trylock(&(shm->requests[i].mutex)) == 0) {
      //      printf("=============================\n"
      //             "Free slot found: %d\n",
      //             i);
            fflush(stdout);
            return i;
        }
    }
    return -1;
}

void free_request(struct Communication* comm, int num) {
	SharedMemory* shm = (SharedMemory*)comm->requestQueue;

   // printf("Freeing cell: %d\n", num);
  //  printf("-> Current string in cell [%d]: %s\n", num, shm->requests[num].text);
    for (int i = 0; i < MAX_TEXT; i++) {
        shm->requests[num].text[i] = 0;
    }
  //  printf("-> After removal cell [%d] content (should be empty): %s\n", num,
  //         shm->requests[num].text);

    pthread_mutex_unlock(&(shm->requests[num].mutex));
}

std::string perform_inference(struct Communication* comm, const char* prompt, int n_tokens_to_gen, int prio, Lora lora, int outb_id)
{
	SharedMemory* shm = (SharedMemory*)comm->requestQueue;
	//printf("Starting call to Guardian inference\n");

	//printf("\n");
	//fflush(stdout);

	//printf("Printing test values\n");
	//printf("Read val: %d\n", shm->test_var);
	//printf("Prio: %d\n", shm->requests[0].prio);

	// TODO: Can defer this in a different queue like in llama-server
	int free_request_slot;
	while(true) {
		free_request_slot = find_free_shm_request(comm);
		if (free_request_slot != -1) {
			break;
		}
	}
	//printf("Got free slot %d\n", free_request_slot);

	int throughput_limit = 99999;
	//printf("[%d] Writing to shm\n", free_request_slot);
	write_to_shm(shm, prompt, n_tokens_to_gen, free_request_slot, prio, lora, throughput_limit, outb_id);
	
	// Notify the server that there is a new request
	sem_post(&shm->requests[free_request_slot].serverNotifier);
	sem_post(&shm->active_reqs);

	// This will block until the server notifies that the request is completed
	std::string result = get_result(comm, strlen(prompt), n_tokens_to_gen, free_request_slot);
	free_request(comm, free_request_slot);

	return result; 
}

void init_guardian()
{
	init_shm(false, &comm);
}

const char* call_guardian(const char* request, const int tokens_to_gen, const int outb_id)
{
	// MAybe I need to malloc?
	std::string result_str = perform_inference(&comm, request, tokens_to_gen, 0, NO_LORA, outb_id).c_str();
	char* result = (char*)malloc(result_str.size() + 1);
	strcpy(result, result_str.c_str());
	return result;
}

void freeme(char* ptr)
{
	free(ptr);
}


void my_ioperm(unsigned short port)
{
	int res = ioperm(port, 4,1);
	if(res != 0) {
		printf("IOPERM ERROR: %s\n", strerror(errno));
	}
}

int main()
{
	Communication comm;
	init_shm(false, &comm);
	SharedMemory* shm = (SharedMemory*)comm.requestQueue;
	printf("test_val: %d\n, prio: %d\n", shm->test_var, shm->requests[0].prio);
	printf("Result: %s\n",perform_inference(&comm, "There is no", 10, 0, NO_LORA, 1).c_str());
	return 0;


}
